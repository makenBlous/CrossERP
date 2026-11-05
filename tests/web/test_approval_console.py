import hashlib
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from crosserp.approval.service import create, submit
from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, ProfitSnapshot, Store
from crosserp.db.session import make_engine, session_scope
from crosserp.web.app import create_app


def _login(client: TestClient, username: str, password: str = "A-password-long") -> None:
    page = client.get("/login")
    token = page.cookies.get("crosserp_login_csrf") or client.cookies.get("crosserp_login_csrf")
    response = client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token, "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _fixture(tmp_path: Path) -> tuple[TestClient, object]:
    url = f"sqlite:///{tmp_path / 'approval-web.sqlite'}"
    app = create_app(url)
    engine = make_engine(url)
    with session_scope(engine) as session:
        operator = create_user(
            session, username="operator", password="A-password-long", roles=(Role.OPERATOR,)
        )
        create_user(session, username="finance", password="A-password-long", roles=(Role.FINANCE,))
        create_user(session, username="auditor", password="A-password-long", roles=(Role.AUDITOR,))
        store = Store(id=None, platform="shopify", marketplace="US", name="demo", currency="USD")
        session.add(store)
        session.flush()
        session.add(
            ProfitSnapshot(
                store_id=store.id,
                period="2026-10",
                internal_sku="SKU-1",
                revenue=Decimal("10"),
                fees=Decimal("1"),
                refunds=Decimal("0"),
                cogs=Decimal("2"),
                freight=Decimal("0"),
                ads=Decimal("0"),
                profit=Decimal("7"),
                currency="USD",
                calc_version="test",
                inputs_hash="a" * 64,
                qty_sold=1,
                qty_refunded=0,
                qty_net=1,
                promotion=Decimal("0"),
                fx_rate=None,
                profit_cny=None,
                ads_included=False,
                status="ok",
                recon_run_id=None,
            )
        )
        row = create(
            session,
            target_type="profit_report",
            target_id="demo:2026-10",
            requested_by=operator.username,
            payload_hash=hashlib.sha256(("a" * 64).encode("ascii")).hexdigest(),
        )
        submit(session, row, actor=operator.username)
    engine.dispose()
    return TestClient(app), url


def test_finance_decision_requires_comment_and_records_user(tmp_path: Path) -> None:
    client, url = _fixture(tmp_path)
    _login(client, "finance")
    page = client.get("/approvals")
    assert page.status_code == 200 and "demo:2026-10" in page.text
    approval_id = page.text.split("/approvals/", 1)[1].split('"', 1)[0]
    csrf = client.cookies.get("crosserp_csrf")
    missing = client.post(
        f"/approvals/{approval_id}/decide",
        data={"action": "approve", "comment": "", "csrf_token": csrf},
    )
    assert missing.status_code == 400
    approved = client.post(
        f"/approvals/{approval_id}/decide",
        data={"action": "approve", "comment": "已核对", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert approved.status_code == 303
    engine = make_engine(url)
    with session_scope(engine) as session:
        row = session.scalar(select(AuditLog).where(AuditLog.action == "approval.approve"))
        assert row is not None and row.approver_id is not None
    engine.dispose()


def test_operator_cannot_decide(tmp_path: Path) -> None:
    client, _ = _fixture(tmp_path)
    _login(client, "operator")
    page = client.get("/approvals")
    approval_id = page.text.split("/approvals/", 1)[1].split('"', 1)[0]
    denied = client.post(
        f"/approvals/{approval_id}/decide",
        data={
            "action": "approve",
            "comment": "尝试",
            "csrf_token": client.cookies.get("crosserp_csrf"),
        },
    )
    assert denied.status_code == 403
