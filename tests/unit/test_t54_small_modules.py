"""T54 小模块错误分支和只读白名单覆盖。"""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from crosserp.agent import tools
from crosserp.audit import checkpoint
from crosserp.auth import security
from crosserp.db.repo import approval as approval_repo
from crosserp.mcp_server import server as mcp_server
from crosserp.profit.report_csv import write_report_csv
from crosserp.web.csrf import login_form_token, token_hash, valid_pair


def test_csrf_security_and_mcp_helpers() -> None:
    assert token_hash("x") == token_hash("x")
    assert valid_pair("x", "x")
    assert not valid_pair("x", "y")
    assert not valid_pair(None, "x")
    assert not valid_pair("", "x")
    issued, must_set = login_form_token(None)
    assert must_set
    assert login_form_token(issued) == (issued, False)
    replaced, replace = login_form_token("not a token")
    assert replace
    assert replaced != "not a token"
    assert security.record_security_event("ignored") is None
    assert "get_profit" in mcp_server.registered_tools()
    assert not set(mcp_server.registered_tools()) & {"export", "approve"}
    with pytest.raises(ModuleNotFoundError):
        mcp_server.create_server()


def test_approval_repository_delegates_to_session() -> None:
    approval = object()

    class Session:
        def get(self, _model: object, _id: object) -> object:
            return approval

        def scalars(self, _statement: object) -> list[object]:
            return [approval]

    session = Session()
    assert approval_repo.get_approval(session, uuid4()) is approval
    assert approval_repo.list_approvals(session) == [approval]


def test_checkpoint_validation_and_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        def scalar(self, _statement: object) -> None:
            return None

        def add(self, value: object) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    monkeypatch.setattr(checkpoint, "append", lambda *args, **kwargs: None)
    session = Session()
    with pytest.raises(ValueError, match="reason"):
        checkpoint.create_checkpoint(session, reason=" ")
    with pytest.raises(ValueError, match="512"):
        checkpoint.create_checkpoint(session, reason="x" * 513)
    row = checkpoint.create_checkpoint(session, reason="daily")
    assert row.reason == "daily"
    assert len(session.added) == 1


def test_readonly_tool_helpers_and_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def fake_agent_session():
        yield SimpleNamespace(
            execute=lambda _statement: [],
            scalars=lambda _statement: [],
            get=lambda _model, _id: None,
            scalar=lambda _statement: None,
        )

    monkeypatch.setattr(tools, "agent_session", fake_agent_session)
    assert tools.get_profit("store", "2026-10").data == []
    assert tools.list_issues(status="open", kind="UNKNOWN", store="demo", limit=1).data == []
    with pytest.raises(ValueError, match="limit"):
        tools.list_issues(limit=0)
    with pytest.raises(ValueError, match="run_id"):
        tools.get_recon_summary()
    with pytest.raises(LookupError, match="结算"):
        tools.get_settlement(str(uuid4()))
    with pytest.raises(LookupError, match="凭证"):
        tools.get_voucher(str(uuid4()))
    with pytest.raises(LookupError, match="对账运行"):
        tools.get_recon_summary(run_id=str(uuid4()))
    assert tools._text(Decimal("1.20")) == "1.20"
    assert tools._text(None) is None
    assert tools._uuid_or_none("bad") is None
    valid_uuid = str(uuid4())
    assert str(tools._uuid_or_none(valid_uuid)) == valid_uuid
    assert tools._cite("table", "id", "field", None).value == ""
    assert tools._limit(200) is None
    with pytest.raises(ValueError):
        tools._limit(201)
    row = SimpleNamespace(
        id=uuid4(),
        period="2026-10",
        internal_sku="SKU-1",
        revenue=Decimal("1"),
        fees=Decimal("0"),
        refunds=Decimal("0"),
        profit=Decimal("1"),
        currency="USD",
        status="ok",
    )
    store = SimpleNamespace(name="demo")
    assert tools._snapshot_data(row, store)["internal_sku"] == "SKU-1"


def test_readonly_tools_return_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    order = SimpleNamespace(
        id=uuid4(), platform_order_id="O-1", platform_sku="SKU-1", qty=2, item_price=Decimal("3")
    )
    settlement = SimpleNamespace(
        id=uuid4(), external_id="SET-1", total=Decimal("10"), currency="USD"
    )
    settlement_line = SimpleNamespace(id=uuid4(), amount=Decimal("10"), sku="SKU-1")
    recon = SimpleNamespace(
        id=uuid4(),
        period="2026-10",
        status="ok",
        groups_total=2,
        groups_matched=2,
        non_order_lines=0,
    )
    approval = SimpleNamespace(
        id=uuid4(), state="approved", requested_by="maker", approver="finance", comment="ok"
    )
    voucher = SimpleNamespace(
        id=uuid4(),
        state="draft",
        period="2026-10",
        total_debit=Decimal("10"),
        total_credit=Decimal("10"),
    )
    line = SimpleNamespace(line_no=1, account_code="1001", debit=Decimal("10"), credit=Decimal("0"))

    class Session:
        def __init__(self, *, row: object = None, rows: list[object] | None = None) -> None:
            self.row = row
            self.rows = rows or []

        def execute(self, _statement: object) -> list[object]:
            return self.rows

        def scalars(self, _statement: object) -> list[object]:
            return self.rows

        def get(self, _model: object, _id: object) -> object:
            return self.row

        def scalar(self, _statement: object) -> object:
            return self.row

    @contextmanager
    def context(session: Session):
        yield session

    monkeypatch.setattr(tools, "agent_session", lambda: context(Session(rows=[order])))
    assert tools.get_order("O-1").data[0]["sku"] == "SKU-1"
    monkeypatch.setattr(
        tools,
        "agent_session",
        lambda: context(Session(row=settlement, rows=[settlement_line])),
    )
    assert tools.get_settlement(str(settlement.id)).data["lines"]
    monkeypatch.setattr(tools, "agent_session", lambda: context(Session(row=recon)))
    assert tools.get_recon_summary(run_id=str(recon.id)).data["groups_total"] == 2
    assert tools.get_recon_summary(store="demo", period="2026-10").data["status"] == "ok"
    monkeypatch.setattr(tools, "agent_session", lambda: context(Session(rows=[approval])))
    assert tools.get_approval_status("profit_report", "r").data[0]["state"] == "approved"
    monkeypatch.setattr(
        tools,
        "agent_session",
        lambda: context(Session(row=voucher, rows=[line])),
    )
    assert tools.get_voucher(str(voucher.id)).data["lines"][0]["account_code"] == "1001"

    monkeypatch.setattr(
        tools,
        "get_profit",
        lambda store, period: tools.ToolResult(
            data=[{"internal_sku": "SKU-1", "profit": "2.00"}], citations=[]
        ),
    )
    compared = tools.compare_profit("demo", "2026-09", "2026-10")
    assert compared.data[0]["difference"] == "0.00"
    rules = tools.search_rules_doc("退款", k=1)
    assert rules.data and rules.citations


def test_report_csv_writes_header_and_rows(tmp_path: Path) -> None:
    snapshot = SimpleNamespace(
        internal_sku="SKU-1",
        currency="USD",
        qty_sold=1,
        qty_refunded=0,
        revenue=Decimal("10"),
        fees=Decimal("1"),
        refunds=Decimal("0"),
        cogs=Decimal("2"),
        freight=Decimal("1"),
        profit=Decimal("6"),
        fx_rate=Decimal("7"),
        profit_cny=Decimal("42"),
        status="ok",
    )
    store = SimpleNamespace(name="demo")

    class Session:
        def execute(self, _statement: object) -> list[tuple[object, object]]:
            return [(snapshot, store)]

    write_report_csv(Session(), period="2026-10", directory=tmp_path)
    text = (tmp_path / "profit.csv").read_text(encoding="utf-8")
    assert "SKU-1" in text and "demo" in text
