"""RawRecord.get 财务原始行详情。白名单与网页 row_detail 一致。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.api.routers import _platform_common
from crosserp.auth.roles import Role
from crosserp.db.repo.imports import (
    insert_import_batch,
    insert_order_line,
    insert_raw_row,
    insert_settlement,
    insert_settlement_line,
)
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    Approval,
    AppUser,
    IamDataScopeRule,
    IamPermissionOverride,
    ImportBatch,
    Issue,
    OrderLine,
    ProfitSnapshot,
    ReconRun,
    Store,
    Voucher,
    VoucherLine,
)
from crosserp.platform.principal import ActorType, Principal

_PASSWORD = "abcdefghij"
_NOW = datetime(2026, 10, 16, tzinfo=UTC)


def _login(client: TestClient, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": _PASSWORD})
    assert response.status_code == 200


def _user(session: Session, username: str, role: Role) -> AppUser:
    return create_user(session, username=username, password=_PASSWORD, roles=(role,))


def _store(name: str, marketplace: str = "US") -> Store:
    return Store(
        id=uuid4(),
        platform="amazon",
        marketplace=marketplace,
        name=name,
        currency="USD",
    )


def _batch(session: Session, file_name: str) -> ImportBatch:
    return insert_import_batch(
        session,
        connector_id="amazon.settlement_v2",
        connector_version="0.1.0",
        file_name=file_name,
        file_sha256=None,
        imported_at=_NOW,
    )


def _scope(session: Session, user_id: UUID, store_id: UUID) -> None:
    session.add(
        IamDataScopeRule(
            name=f"rows-{store_id}",
            entity="*",
            scope_type="storeIds",
            values=[str(store_id)],
            updated_by=user_id,
            updated_at=_NOW,
        )
    )


def _order(
    session: Session, store: Store, *, file_name: str, price: Decimal
) -> tuple[OrderLine, int]:
    batch = _batch(session, file_name)
    raw = insert_raw_row(
        session,
        batch_id=batch.id,
        row_no=7,
        payload={"sku": "TENT-2P", "amount": str(price)},
    )
    line = insert_order_line(
        session,
        store_id=store.id,
        platform_order_id="ORDER-1",
        order_item_id=None,
        platform_sku="TENT-2P",
        qty=2,
        order_date=_NOW,
        item_price=price,
        currency="USD",
        source_batch_id=batch.id,
        raw_row_id=raw.id,
    )
    return line, raw.id


def _get(client: TestClient, table: str, row_id: object):
    return client.get(f"/api/v1/finance/rows/{table}/{row_id}")


def test_order_line_returns_money_minor_and_source_file(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "rows-order", Role.ADMIN)
        store = _store("订单店")
        session.add(store)
        session.flush()
        line, _raw_id = _order(session, store, file_name="orders.tsv", price=Decimal("12.3400"))
        line_id = line.id
        store_id = store.id

    _login(json_client, "rows-order")
    response = _get(json_client, "order_line", line_id)
    assert response.status_code == 200
    body = response.json()
    assert body["table"] == "order_line"
    assert body["id"] == str(line_id)
    assert body["sourceFile"] == "orders.tsv"
    assert body["fields"]["itemPrice"] == {"amountMinor": 123400, "currency": "USD"}
    assert isinstance(body["fields"]["itemPrice"]["amountMinor"], int)
    assert body["fields"]["storeId"] == str(store_id)
    assert body["fields"]["qty"] == 2


def test_unknown_table_and_bad_id_are_not_found(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "rows-unknown", Role.ADMIN)
        store = _store("未知表店")
        session.add(store)
        session.flush()
        line, _raw_id = _order(session, store, file_name="known.tsv", price=Decimal("1.0000"))
        line_id = line.id

    _login(json_client, "rows-unknown")
    unknown = _get(json_client, "settlement", line_id)
    star = _get(json_client, "app_user", line_id)
    bad_uuid = _get(json_client, "order_line", "1")
    bad_raw = _get(json_client, "raw_row", line_id)
    missing = _get(json_client, "order_line", uuid4())
    assert unknown.status_code == star.status_code == 404
    assert bad_uuid.status_code == bad_raw.status_code == missing.status_code == 404
    assert unknown.json()["code"] == "NOT_FOUND"
    assert star.json()["code"] == bad_uuid.json()["code"] == "NOT_FOUND"
    assert "password" not in unknown.text
    assert "TENT-2P" not in unknown.text
    assert str(line_id) not in unknown.text


def test_raw_row_integer_id_requires_in_scope_projection(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "rows-raw", Role.ADMIN)
        visible = _store("可见原始店")
        hidden = _store("隐藏原始店", "DE")
        session.add_all([visible, hidden])
        session.flush()
        _scope(session, user.id, visible.id)
        _line, visible_raw = _order(
            session, visible, file_name="visible-raw.tsv", price=Decimal("1.0000")
        )
        _hidden_line, hidden_raw = _order(
            session, hidden, file_name="hidden-raw.tsv", price=Decimal("9.0000")
        )
        orphan_batch = _batch(session, "orphan.tsv")
        orphan = insert_raw_row(
            session,
            batch_id=orphan_batch.id,
            row_no=3,
            payload={"sku": "ORPHAN"},
        )
        orphan_id = orphan.id

    _login(json_client, "rows-raw")
    visible_response = _get(json_client, "raw_row", visible_raw)
    hidden_response = _get(json_client, "raw_row", hidden_raw)
    orphan_response = _get(json_client, "raw_row", orphan_id)
    assert visible_response.status_code == 200
    body = visible_response.json()
    assert body["id"] == visible_raw
    assert isinstance(body["id"], int)
    assert body["rowNo"] == 7
    assert body["sourceFile"] == "visible-raw.tsv"
    assert body["payload"] == {"sku": "TENT-2P", "amount": "1.0000"}
    assert hidden_response.status_code == orphan_response.status_code == 404
    assert hidden_response.json()["code"] == orphan_response.json()["code"] == "NOT_FOUND"


def test_raw_row_linked_to_an_out_of_scope_store_is_hidden(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "rows-mixed", Role.ADMIN)
        visible = _store("混合可见")
        hidden = _store("混合隐藏", "DE")
        session.add_all([visible, hidden])
        session.flush()
        _scope(session, user.id, visible.id)
        batch = _batch(session, "mixed.tsv")
        raw = insert_raw_row(session, batch_id=batch.id, row_no=4, payload={"sku": "MIX"})
        insert_order_line(
            session,
            store_id=visible.id,
            platform_order_id="MIX-VIS",
            order_item_id=None,
            platform_sku="MIX",
            qty=1,
            order_date=_NOW,
            item_price=Decimal("1.0000"),
            currency="USD",
            source_batch_id=batch.id,
            raw_row_id=raw.id,
        )
        settlement = insert_settlement(
            session,
            store_id=hidden.id,
            platform="amazon",
            external_id="MIX-HID",
            period_start=_NOW,
            period_end=_NOW,
            deposit_date=None,
            total=Decimal("1.0000"),
            currency="EUR",
            source_batch_id=batch.id,
        )
        insert_settlement_line(
            session,
            settlement_id=settlement.id,
            transaction_type="Order",
            order_id="MIX-HID",
            order_item_code=None,
            sku="MIX",
            qty=1,
            amount_type="ItemPrice",
            amount_description="Principal",
            amount=Decimal("1.0000"),
            posted_at=_NOW,
            raw_row_id=raw.id,
        )
        raw_id = raw.id

    _login(json_client, "rows-mixed")
    response = _get(json_client, "raw_row", raw_id)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert "MIX" not in response.text


def test_store_scope_hides_direct_and_parent_rows(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "rows-scope", Role.ADMIN)
        visible = _store("范围店")
        hidden = _store("范围外店", "DE")
        session.add_all([visible, hidden])
        session.flush()
        _scope(session, user.id, visible.id)
        visible_line, _raw = _order(
            session, visible, file_name="scope-visible.tsv", price=Decimal("1.2500")
        )
        hidden_line, _hidden_raw = _order(
            session, hidden, file_name="scope-hidden.tsv", price=Decimal("8.0000")
        )
        visible_batch = _batch(session, "settle-visible.tsv")
        hidden_batch = _batch(session, "settle-hidden.tsv")
        visible_settlement = insert_settlement(
            session,
            store_id=visible.id,
            platform="amazon",
            external_id="SET-VIS",
            period_start=_NOW,
            period_end=_NOW,
            deposit_date=None,
            total=Decimal("2.0000"),
            currency="USD",
            source_batch_id=visible_batch.id,
        )
        hidden_settlement = insert_settlement(
            session,
            store_id=hidden.id,
            platform="amazon",
            external_id="SET-HID",
            period_start=_NOW,
            period_end=_NOW,
            deposit_date=None,
            total=Decimal("3.0000"),
            currency="EUR",
            source_batch_id=hidden_batch.id,
        )
        visible_raw = insert_raw_row(
            session, batch_id=visible_batch.id, row_no=1, payload={"side": "visible"}
        )
        hidden_raw = insert_raw_row(
            session, batch_id=hidden_batch.id, row_no=1, payload={"side": "hidden"}
        )
        visible_settlement_line = insert_settlement_line(
            session,
            settlement_id=visible_settlement.id,
            transaction_type="Order",
            order_id="O-1",
            order_item_code=None,
            sku="SKU",
            qty=1,
            amount_type="ItemPrice",
            amount_description="Principal",
            amount=Decimal("2.5000"),
            posted_at=_NOW,
            raw_row_id=visible_raw.id,
        )
        hidden_settlement_line = insert_settlement_line(
            session,
            settlement_id=hidden_settlement.id,
            transaction_type="Order",
            order_id="O-2",
            order_item_code=None,
            sku="SKU",
            qty=1,
            amount_type="ItemPrice",
            amount_description="Principal",
            amount=Decimal("3.0000"),
            posted_at=_NOW,
            raw_row_id=hidden_raw.id,
        )
        visible_snapshot = ProfitSnapshot(
            store_id=visible.id,
            period="2026-10",
            internal_sku="SKU-1",
            revenue=Decimal("10.0000"),
            fees=Decimal("1.0000"),
            refunds=Decimal("0.0000"),
            cogs=Decimal("0.0000"),
            freight=Decimal("0.0000"),
            profit=Decimal("9.0000"),
            currency="USD",
            calc_version="profit-v1",
            inputs_hash="a" * 64,
            fx_rate=Decimal("7.10000000"),
            profit_cny=Decimal("70.0000"),
        )
        hidden_snapshot = ProfitSnapshot(
            store_id=hidden.id,
            period="2026-10",
            internal_sku="SKU-2",
            revenue=Decimal("9.0000"),
            fees=Decimal("1.0000"),
            refunds=Decimal("0.0000"),
            cogs=Decimal("0.0000"),
            freight=Decimal("0.0000"),
            profit=Decimal("8.0000"),
            currency="EUR",
            calc_version="profit-v1",
            inputs_hash="b" * 64,
        )
        session.add_all([visible_snapshot, hidden_snapshot])
        session.flush()
        visible_ids = {
            "order_line": visible_line.id,
            "settlement_line": visible_settlement_line.id,
            "profit_snapshot": visible_snapshot.id,
        }
        hidden_ids = {
            "order_line": hidden_line.id,
            "settlement_line": hidden_settlement_line.id,
            "profit_snapshot": hidden_snapshot.id,
        }

    _login(json_client, "rows-scope")
    for table, row_id in visible_ids.items():
        response = _get(json_client, table, row_id)
        assert response.status_code == 200, table
    settlement_body = _get(json_client, "settlement_line", visible_ids["settlement_line"]).json()
    assert settlement_body["fields"]["amount"] == {"amountMinor": 25000, "currency": "USD"}
    assert settlement_body["sourceFile"] == "settle-visible.tsv"
    profit_body = _get(json_client, "profit_snapshot", visible_ids["profit_snapshot"]).json()
    assert profit_body["fields"]["revenue"]["amountMinor"] == 100000
    assert profit_body["fields"]["profitCny"] == {"amountMinor": 700000, "currency": "CNY"}
    assert profit_body["fields"]["fxRate"] == "7.10000000"
    assert isinstance(profit_body["fields"]["fxRate"], str)
    for table, row_id in hidden_ids.items():
        hidden_response = _get(json_client, table, row_id)
        missing = _get(json_client, table, uuid4())
        assert hidden_response.status_code == missing.status_code == 404, table
        assert hidden_response.json()["code"] == missing.json()["code"] == "NOT_FOUND"


def test_issue_and_voucher_line_follow_parent_store(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "rows-parent", Role.ADMIN)
        visible = _store("父级可见")
        hidden = _store("父级隐藏", "DE")
        session.add_all([visible, hidden])
        session.flush()
        _scope(session, user.id, visible.id)
        visible_line, _raw = _order(
            session, visible, file_name="parent-visible.tsv", price=Decimal("1.0000")
        )
        hidden_line, _hidden_raw = _order(
            session, hidden, file_name="parent-hidden.tsv", price=Decimal("1.0000")
        )
        visible_run = ReconRun(
            store_id=visible.id,
            period="2026-10",
            as_of=date(2026, 10, 16),
            rule_set_version="recon-v1",
            started_at=_NOW,
            status="done",
            groups_total=1,
            groups_matched=1,
            non_order_lines=0,
        )
        hidden_run = ReconRun(
            store_id=hidden.id,
            period="2026-10",
            as_of=date(2026, 10, 16),
            rule_set_version="recon-v1",
            started_at=_NOW,
            status="done",
            groups_total=1,
            groups_matched=0,
            non_order_lines=0,
        )
        session.add_all([visible_run, hidden_run])
        session.flush()
        linked = Issue(
            kind="unmatched",
            severity="high",
            order_line_id=visible_line.id,
            detail_json={"reason": "AMOUNT_MISMATCH"},
            status="open",
            created_at=_NOW,
        )
        hidden_issue = Issue(
            kind="unmatched",
            severity="high",
            order_line_id=hidden_line.id,
            detail_json={"reason": "HIDDEN"},
            status="open",
            created_at=_NOW,
        )
        mixed = Issue(
            kind="unmatched",
            severity="high",
            order_line_id=visible_line.id,
            recon_run_id=hidden_run.id,
            detail_json={"reason": "MIXED"},
            status="open",
            created_at=_NOW,
        )
        unlinked = Issue(
            kind="parse",
            severity="low",
            detail_json={"reason": "NO_STORE"},
            status="open",
            created_at=_NOW,
        )
        run_issue = Issue(
            kind="unmatched",
            severity="low",
            recon_run_id=visible_run.id,
            detail_json={"reason": "RUN"},
            status="open",
            created_at=_NOW,
        )
        visible_voucher = Voucher(
            store_id=visible.id,
            period="2026-10",
            source_type="month",
            source_id="parent-visible",
            state="draft",
            currency="USD",
            total_debit=Decimal("4.0000"),
            total_credit=Decimal("4.0000"),
            inputs_hash="c" * 64,
            accounts_hash="d" * 64,
            created_by="rows-parent",
            created_at=_NOW,
        )
        hidden_voucher = Voucher(
            store_id=hidden.id,
            period="2026-10",
            source_type="month",
            source_id="parent-hidden",
            state="draft",
            currency="EUR",
            total_debit=Decimal("5.0000"),
            total_credit=Decimal("5.0000"),
            inputs_hash="e" * 64,
            accounts_hash="f" * 64,
            created_by="rows-parent",
            created_at=_NOW,
        )
        session.add_all(
            [
                linked,
                hidden_issue,
                mixed,
                unlinked,
                run_issue,
                visible_voucher,
                hidden_voucher,
            ]
        )
        session.flush()
        visible_voucher_line = VoucherLine(
            voucher_id=visible_voucher.id,
            line_no=1,
            account_key="sales",
            account_code="6001",
            account_name="主营业务收入",
            debit=Decimal("0.0000"),
            credit=Decimal("4.0000"),
            summary="收入",
            source_ref="parent-visible",
        )
        hidden_voucher_line = VoucherLine(
            voucher_id=hidden_voucher.id,
            line_no=1,
            account_key="sales",
            account_code="6001",
            account_name="主营业务收入",
            debit=Decimal("0.0000"),
            credit=Decimal("5.0000"),
            summary="收入",
            source_ref="parent-hidden",
        )
        session.add_all([visible_voucher_line, hidden_voucher_line])
        session.flush()
        linked_id = linked.id
        hidden_issue_id = hidden_issue.id
        mixed_id = mixed.id
        unlinked_id = unlinked.id
        run_issue_id = run_issue.id
        voucher_id = visible_voucher.id
        hidden_voucher_id = hidden_voucher.id
        voucher_line_id = visible_voucher_line.id
        hidden_voucher_line_id = hidden_voucher_line.id

    _login(json_client, "rows-parent")
    linked_response = _get(json_client, "issue", linked_id)
    run_response = _get(json_client, "issue", run_issue_id)
    voucher_response = _get(json_client, "voucher", voucher_id)
    line_response = _get(json_client, "voucher_line", voucher_line_id)
    assert linked_response.status_code == run_response.status_code == 200
    assert voucher_response.status_code == line_response.status_code == 200
    assert voucher_response.json()["fields"]["totalDebit"] == {
        "amountMinor": 40000,
        "currency": "USD",
    }
    assert line_response.json()["fields"]["credit"] == {"amountMinor": 40000, "currency": "USD"}
    for row_id, table in (
        (hidden_issue_id, "issue"),
        (mixed_id, "issue"),
        (unlinked_id, "issue"),
        (hidden_voucher_id, "voucher"),
        (hidden_voucher_line_id, "voucher_line"),
    ):
        denied = _get(json_client, table, row_id)
        assert denied.status_code == 404
        assert denied.json()["code"] == "NOT_FOUND"


def test_approval_visible_only_when_target_store_is_in_scope(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "rows-approval", Role.ADMIN)
        visible = _store("审批可见")
        hidden = _store("审批隐藏", "DE")
        session.add_all([visible, hidden])
        session.flush()
        _scope(session, user.id, visible.id)
        visible_voucher = Voucher(
            store_id=visible.id,
            period="2026-10",
            source_type="month",
            source_id="approval-visible",
            state="draft",
            currency="USD",
            total_debit=Decimal("1.0000"),
            total_credit=Decimal("1.0000"),
            inputs_hash="1" * 64,
            accounts_hash="2" * 64,
            created_by="rows-approval",
            created_at=_NOW,
        )
        hidden_voucher = Voucher(
            store_id=hidden.id,
            period="2026-10",
            source_type="month",
            source_id="approval-hidden",
            state="draft",
            currency="EUR",
            total_debit=Decimal("1.0000"),
            total_credit=Decimal("1.0000"),
            inputs_hash="3" * 64,
            accounts_hash="4" * 64,
            created_by="rows-approval",
            created_at=_NOW,
        )
        session.add(
            ProfitSnapshot(
                store_id=visible.id,
                period="2026-10",
                internal_sku="SKU-A",
                revenue=Decimal("1.0000"),
                fees=Decimal("0.0000"),
                refunds=Decimal("0.0000"),
                cogs=Decimal("0.0000"),
                freight=Decimal("0.0000"),
                profit=Decimal("1.0000"),
                currency="USD",
                calc_version="profit-v1",
                inputs_hash="5" * 64,
            )
        )
        session.add_all([visible_voucher, hidden_voucher])
        session.flush()
        visible_approval = Approval(
            target_type="voucher",
            target_id=str(visible_voucher.id),
            state="pending",
            requested_by="rows-approval",
            requested_at=_NOW,
        )
        hidden_approval = Approval(
            target_type="voucher",
            target_id=str(hidden_voucher.id),
            state="pending",
            requested_by="rows-approval",
            requested_at=_NOW,
        )
        report_approval = Approval(
            target_type="profit_report",
            target_id="审批可见:2026-10",
            state="pending",
            requested_by="rows-approval",
            requested_at=_NOW,
        )
        batch_approval = Approval(
            target_type="import_batch",
            target_id=str(uuid4()),
            state="pending",
            requested_by="rows-approval",
            requested_at=_NOW,
        )
        session.add_all([visible_approval, hidden_approval, report_approval, batch_approval])
        session.flush()
        visible_id = visible_approval.id
        hidden_id = hidden_approval.id
        report_id = report_approval.id
        batch_id = batch_approval.id

    _login(json_client, "rows-approval")
    visible_response = _get(json_client, "approval", visible_id)
    report_response = _get(json_client, "approval", report_id)
    assert visible_response.status_code == report_response.status_code == 200
    assert visible_response.json()["fields"]["targetType"] == "voucher"
    assert report_response.json()["fields"]["targetId"] == "审批可见:2026-10"
    for row_id in (hidden_id, batch_id, uuid4()):
        denied = _get(json_client, "approval", row_id)
        assert denied.status_code == 404
        assert denied.json()["code"] == "NOT_FOUND"


def test_login_permission_and_amount_field_gate(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "rows-no-perm", Role.OPERATOR)
        stripped = _user(session, "rows-no-cost", Role.ADMIN)
        session.add(
            IamPermissionOverride(
                user_id=stripped.id,
                permission="sku.cost:read",
                effect="deny",
                reason="裁剪金额",
                data_scopes=[],
                created_at=_NOW,
            )
        )
        store = _store("权限店")
        session.add(store)
        session.flush()
        line, _raw = _order(session, store, file_name="perm.tsv", price=Decimal("6.0000"))
        line_id = line.id

    anonymous = _get(json_client, "order_line", line_id)
    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "AUTH_REQUIRED"

    _login(json_client, "rows-no-perm")
    denied = _get(json_client, "order_line", line_id)
    missing = _get(json_client, "order_line", uuid4())
    assert denied.status_code == missing.status_code == 404
    assert denied.json()["code"] == "FORBIDDEN"

    json_client.cookies.clear()
    _login(json_client, "rows-no-cost")
    stripped_response = _get(json_client, "order_line", line_id)
    assert stripped_response.status_code == 200
    fields = stripped_response.json()["fields"]
    assert "itemPrice" not in fields
    assert fields["platformSku"] == "TENT-2P"


def test_agent_reads_only_with_represented_permission(
    json_client: TestClient, api_engine, monkeypatch
) -> None:
    with Session(api_engine) as session, session.begin():
        viewer = _user(session, "rows-agent-yes", Role.ADMIN)
        blocked = _user(session, "rows-agent-no", Role.VIEWER)
        store = _store("智能体店")
        session.add(store)
        session.flush()
        line, _raw = _order(session, store, file_name="agent.tsv", price=Decimal("2.5000"))
        line_id = line.id
        viewer_id = viewer.id
        blocked_id = blocked.id

    def _as(user_id: UUID) -> None:
        principal = Principal(
            user_id=user_id,
            actor_type=ActorType.AGENT,
            agent_id="rows-agent",
            on_behalf_of=user_id,
            channel="mcp",
        )
        monkeypatch.setattr(_platform_common, "get_principal", lambda _request: principal)

    _as(viewer_id)
    allowed = _get(json_client, "order_line", line_id)
    assert allowed.status_code == 200
    assert allowed.json()["fields"]["itemPrice"]["amountMinor"] == 25000

    _as(blocked_id)
    denied = _get(json_client, "order_line", line_id)
    assert denied.status_code == 404
    assert denied.json()["code"] == "FORBIDDEN"


def test_endpoint_metadata_matches_openapi(json_client: TestClient) -> None:
    spec = json_client.get("/openapi.json")
    assert spec.status_code == 200
    operation = spec.json()["paths"]["/api/v1/finance/rows/{table}/{id}"]["get"]
    meta = operation["x-crosserp"]
    assert meta["entity"] == "RawRecord"
    assert meta["action"] == "RawRecord.get"
    assert meta["permission"] == "integration:read"
    assert meta["riskTier"] == "none"
