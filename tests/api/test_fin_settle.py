"""Settlement.list / Settlement.get 已落库结算的只读 JSON 接口。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.routers import _platform_common
from crosserp.auth.roles import Role
from crosserp.connectors.amazon_settlement_v2 import AmazonSettlementV2Connector
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus
from crosserp.core.money import to_amount_minor
from crosserp.db.repo.imports import (
    insert_fee,
    insert_import_batch,
    insert_raw_row,
    insert_settlement,
    insert_settlement_line,
)
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    Fee,
    IamDataScopeRule,
    IamPermissionOverride,
    Settlement,
    SettlementLine,
    Store,
)
from crosserp.platform.principal import ActorType, Principal

_REPO = Path(__file__).resolve().parents[2]
_AMAZON_SAMPLE = _REPO / "samples" / "synthetic" / "amazon_us_2026-10-01_2026-10-14.tsv"
_PASSWORD = "abcdefghij"


def _login(client: TestClient, username: str, password: str = _PASSWORD) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _user(session: Session, username: str, *roles: Role):
    return create_user(session, username=username, password=_PASSWORD, roles=roles)


def _store(name: str, marketplace: str = "US") -> Store:
    return Store(
        id=uuid4(),
        platform="amazon",
        marketplace=marketplace,
        name=name,
        currency="USD",
    )


def _seed(
    session: Session,
    store: Store,
    *,
    external_id: str,
    total: Decimal,
    period_end: datetime,
    lines: tuple[tuple[Decimal, str | None], ...] = (),
) -> UUID:
    batch = insert_import_batch(
        session,
        connector_id="amazon.settlement_v2",
        connector_version="0.1.0",
        file_name=f"{external_id}.tsv",
        file_sha256=None,
        imported_at=datetime(2026, 10, 16, tzinfo=UTC),
    )
    settlement = insert_settlement(
        session,
        store_id=store.id,
        platform="amazon",
        external_id=external_id,
        period_start=datetime(2026, 10, 1, tzinfo=UTC),
        period_end=period_end,
        deposit_date=None,
        total=total,
        currency="USD",
        source_batch_id=batch.id,
    )
    for index, (amount, fee_category) in enumerate(lines, start=1):
        raw = insert_raw_row(
            session,
            batch_id=batch.id,
            row_no=index,
            payload={"external-id": external_id, "amount": str(amount)},
        )
        line = insert_settlement_line(
            session,
            settlement_id=settlement.id,
            transaction_type="Order",
            order_id=f"ORDER-{index}",
            order_item_code=None,
            sku="SKU-1",
            qty=1,
            amount_type="ItemPrice",
            amount_description="Principal",
            amount=amount,
            posted_at=datetime(2026, 10, index, tzinfo=UTC),
            raw_row_id=raw.id,
        )
        if fee_category is not None:
            insert_fee(
                session,
                settlement_line_id=line.id,
                fee_category=fee_category,
                amount=amount,
            )
    return settlement.id


def _minor(amount: Decimal) -> int:
    return to_amount_minor(amount)


def _grant_amount(session: Session, user_id: UUID) -> None:
    session.add(
        IamPermissionOverride(
            user_id=user_id,
            permission="sku.cost:read",
            effect="allow",
            reason="结算金额字段",
            data_scopes=[],
            created_at=datetime.now(UTC),
        )
    )


def test_settlement_list_paginates_sorts_and_searches(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "settle-list-user", Role.OPERATOR)
        _grant_amount(session, user.id)
        store = _store("美国店")
        session.add(store)
        session.flush()
        first = _seed(
            session,
            store,
            external_id="SETTLE-A",
            total=Decimal("10.0000"),
            period_end=datetime(2026, 10, 14, tzinfo=UTC),
        )
        second = _seed(
            session,
            store,
            external_id="SETTLE-B",
            total=Decimal("30.0000"),
            period_end=datetime(2026, 10, 7, tzinfo=UTC),
        )
        _seed(
            session,
            store,
            external_id="OTHER-C",
            total=Decimal("20.0000"),
            period_end=datetime(2026, 10, 21, tzinfo=UTC),
        )
        assert user.id is not None
        first_id = str(first)
        second_id = str(second)

    _login(json_client, "settle-list-user")
    listed = json_client.get(
        "/api/v1/finance/settlements",
        params={"q": "settle", "page": 1, "pageSize": 1, "sort": "externalId"},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pageSize"] == 1
    assert [item["id"] for item in body["items"]] == [first_id]
    assert body["items"][0]["storeName"] == "美国店"
    assert body["items"][0]["netPayout"] == {"amountMinor": 100000, "currency": "USD"}
    assert isinstance(body["items"][0]["netPayout"]["amountMinor"], int)

    second_page = json_client.get(
        "/api/v1/finance/settlements",
        params={"q": "SETTLE", "page": 2, "pageSize": 1, "sort": "externalId"},
    )
    assert [item["id"] for item in second_page.json()["items"]] == [second_id]

    by_payout = json_client.get(
        "/api/v1/finance/settlements",
        params={"q": "SETTLE", "sort": "-netPayout", "pageSize": 10},
    )
    assert [item["externalId"] for item in by_payout.json()["items"]] == ["SETTLE-B", "SETTLE-A"]

    default_page = json_client.get("/api/v1/finance/settlements", params={"q": "OTHER-C"})
    assert default_page.json()["pageSize"] == 20
    assert default_page.json()["items"][0]["periodEnd"] == "2026-10-21T00:00:00+00:00"

    invalid = json_client.get("/api/v1/finance/settlements", params={"sort": "createdAt"})
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "VALIDATION_FAILED"


def test_settlement_get_returns_line_summary_in_amount_minor(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        viewer = _user(session, "settle-detail-user", Role.VIEWER)
        _grant_amount(session, viewer.id)
        store = _store("明细店")
        session.add(store)
        session.flush()
        settlement_id = _seed(
            session,
            store,
            external_id="SETTLE-MINOR",
            total=Decimal("1.2345"),
            period_end=datetime(2026, 10, 14, tzinfo=UTC),
            lines=(
                (Decimal("12.3400"), "principal"),
                (Decimal("-0.0001"), "commission"),
                (Decimal("0.5000"), None),
            ),
        )

    _login(json_client, "settle-detail-user")
    response = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["netPayout"] == {"amountMinor": 12345, "currency": "USD"}
    assert isinstance(body["netPayout"]["amountMinor"], int)
    assert body["lineSummary"]["lineCount"] == 3
    assert body["lineSummary"]["total"] == {"amountMinor": 128399, "currency": "USD"}
    categories = {
        item["feeCategory"]: item["amount"]["amountMinor"]
        for item in body["lineSummary"]["byFeeCategory"]
    }
    assert categories == {"commission": -1, "principal": 123400}
    assert [line["feeCategory"] for line in body["lines"]] == ["principal", "commission", None]
    assert body["lines"][1]["amount"] == {"amountMinor": -1, "currency": "USD"}
    assert body["provenance"]["rawRecordIds"]
    assert all(isinstance(row_id, int) for row_id in body["provenance"]["rawRecordIds"])


def test_settlement_scope_filters_list_and_hides_single_row(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "settle-scope-user", Role.FINANCE)
        visible = _store("可见店")
        hidden = _store("隐藏店", "DE")
        session.add_all([visible, hidden])
        session.flush()
        visible_id = _seed(
            session,
            visible,
            external_id="SETTLE-VISIBLE",
            total=Decimal("1.0000"),
            period_end=datetime(2026, 10, 2, tzinfo=UTC),
        )
        hidden_id = _seed(
            session,
            hidden,
            external_id="SETTLE-HIDDEN",
            total=Decimal("9.0000"),
            period_end=datetime(2026, 10, 3, tzinfo=UTC),
        )
        session.add(
            IamDataScopeRule(
                name="settle-scope",
                entity="*",
                scope_type="storeIds",
                values=[str(visible.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )

    _login(json_client, "settle-scope-user")
    listed = json_client.get("/api/v1/finance/settlements", params={"q": "SETTLE", "pageSize": 1})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == str(visible_id)
    assert listed.json()["items"][0]["externalId"] == "SETTLE-VISIBLE"

    visible_response = json_client.get(f"/api/v1/finance/settlements/{visible_id}")
    hidden_response = json_client.get(f"/api/v1/finance/settlements/{hidden_id}")
    missing = json_client.get(f"/api/v1/finance/settlements/{uuid4()}")
    assert visible_response.status_code == 200
    assert hidden_response.status_code == missing.status_code == 404
    assert hidden_response.json()["code"] == missing.json()["code"] == "NOT_FOUND"


def test_settlement_requires_login_and_hides_unauthorized(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "settle-no-perm")
        store = _store("无权店")
        session.add(store)
        session.flush()
        settlement_id = _seed(
            session,
            store,
            external_id="SETTLE-SECRET",
            total=Decimal("1.0000"),
            period_end=datetime(2026, 10, 4, tzinfo=UTC),
        )

    anonymous_list = json_client.get("/api/v1/finance/settlements")
    anonymous_get = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert anonymous_list.status_code == anonymous_get.status_code == 401
    assert anonymous_list.json()["code"] == anonymous_get.json()["code"] == "AUTH_REQUIRED"

    _login(json_client, "settle-no-perm")
    denied_list = json_client.get("/api/v1/finance/settlements")
    denied_get = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    missing = json_client.get(f"/api/v1/finance/settlements/{uuid4()}")
    assert denied_list.status_code == denied_get.status_code == missing.status_code == 404
    assert denied_list.json()["code"] == "FORBIDDEN"


def test_settlement_agent_l1_reads_with_represented_permission(
    json_client: TestClient, api_engine, monkeypatch
) -> None:
    with Session(api_engine) as session, session.begin():
        viewer = _user(session, "settle-agent-viewer", Role.VIEWER)
        _grant_amount(session, viewer.id)
        blocked = _user(session, "settle-agent-blocked")
        store = _store("智能体店")
        session.add(store)
        session.flush()
        settlement_id = _seed(
            session,
            store,
            external_id="SETTLE-AGENT",
            total=Decimal("2.5000"),
            period_end=datetime(2026, 10, 5, tzinfo=UTC),
        )
        viewer_id = viewer.id
        blocked_id = blocked.id

    def _as(user_id: UUID) -> None:
        principal = Principal(
            user_id=user_id,
            actor_type=ActorType.AGENT,
            agent_id="settle-agent",
            on_behalf_of=user_id,
            channel="mcp",
            permissions=frozenset({"report:read"}),
        )
        monkeypatch.setattr(_platform_common, "get_principal", lambda _request: principal)

    _as(viewer_id)
    allowed = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert allowed.status_code == 200
    assert allowed.json()["netPayout"]["amountMinor"] == 25000

    _as(blocked_id)
    denied = json_client.get("/api/v1/finance/settlements")
    denied_get = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert denied.status_code == denied_get.status_code == 404


def test_settlement_api_reads_amazon_v2_stored_rows(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        amazon_user = _user(session, "settle-amazon-user", Role.OPERATOR)
        _grant_amount(session, amazon_user.id)
        result = import_file(session, _AMAZON_SAMPLE, AmazonSettlementV2Connector())
        assert result.status is ImportStatus.DONE
        settlement = session.scalars(select(Settlement)).one()
        lines = list(
            session.scalars(
                select(SettlementLine).where(SettlementLine.settlement_id == settlement.id)
            )
        )
        fees = list(
            session.scalars(
                select(Fee)
                .join(SettlementLine, SettlementLine.id == Fee.settlement_line_id)
                .where(SettlementLine.settlement_id == settlement.id)
            )
        )
        settlement_id = settlement.id
        expected_payout = _minor(settlement.total)
        expected_line_total = _minor(sum((line.amount for line in lines), Decimal(0)))
        expected_line_count = len(lines)
        expected_fees: dict[str, int] = {}
        for fee in fees:
            expected_fees[fee.fee_category] = expected_fees.get(fee.fee_category, 0) + _minor(
                fee.amount
            )
        external_id = settlement.external_id

    _login(json_client, "settle-amazon-user")
    listed = json_client.get("/api/v1/finance/settlements", params={"q": external_id})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["netPayout"]["amountMinor"] == expected_payout

    detail = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["externalId"] == external_id
    assert body["platform"] == "amazon"
    assert body["netPayout"]["amountMinor"] == expected_payout
    assert body["lineSummary"]["lineCount"] == expected_line_count
    assert body["lineSummary"]["total"]["amountMinor"] == expected_line_total
    assert {
        item["feeCategory"]: item["amount"]["amountMinor"]
        for item in body["lineSummary"]["byFeeCategory"]
    } == expected_fees
    assert len(body["lines"]) == expected_line_count


def test_settlement_other_store_is_hidden_and_empty_scope_is_empty(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "settle-store-a", Role.FINANCE)
        _grant_amount(session, user.id)
        visible = _store("店铺A")
        hidden = _store("店铺B", "DE")
        session.add_all([visible, hidden])
        session.flush()
        visible_id = _seed(
            session,
            visible,
            external_id="SETTLE-A-ONLY",
            total=Decimal("3.0000"),
            period_end=datetime(2026, 10, 8, tzinfo=UTC),
        )
        hidden_id = _seed(
            session,
            hidden,
            external_id="SETTLE-B-ONLY",
            total=Decimal("8.0000"),
            period_end=datetime(2026, 10, 9, tzinfo=UTC),
        )
        session.add(
            IamDataScopeRule(
                name="settle-store-a",
                entity="Settlement",
                scope_type="storeIds",
                values=[str(visible.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )

    _login(json_client, "settle-store-a")
    listed = json_client.get("/api/v1/finance/settlements", params={"pageSize": 50})
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()["items"]} == {str(visible_id)}
    assert json_client.get(f"/api/v1/finance/settlements/{hidden_id}").status_code == 404
    assert json_client.get(f"/api/v1/finance/settlements/{visible_id}").status_code == 200

    with Session(api_engine) as session, session.begin():
        rule = session.scalars(select(IamDataScopeRule)).one()
        rule.values = []

    empty = json_client.get("/api/v1/finance/settlements", params={"pageSize": 50})
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 0
    assert json_client.get(f"/api/v1/finance/settlements/{visible_id}").status_code == 404


def test_settlement_hides_amounts_without_field_permission(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "settle-no-amount", Role.VIEWER)
        store = _store("无金额店")
        session.add(store)
        session.flush()
        settlement_id = _seed(
            session,
            store,
            external_id="SETTLE-NO-AMOUNT",
            total=Decimal("4.0000"),
            period_end=datetime(2026, 10, 10, tzinfo=UTC),
            lines=((Decimal("4.0000"), "principal"),),
        )

    _login(json_client, "settle-no-amount")
    listed = json_client.get("/api/v1/finance/settlements", params={"q": "SETTLE-NO-AMOUNT"})
    assert listed.status_code == 200
    assert "netPayout" not in listed.json()["items"][0]
    detail = json_client.get(f"/api/v1/finance/settlements/{settlement_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert "netPayout" not in body
    assert "amount" not in body["lines"][0]
    assert "total" not in body["lineSummary"]
    assert "amount" not in body["lineSummary"]["byFeeCategory"][0]


def test_settlement_openapi_metadata(json_client: TestClient) -> None:
    paths = json_client.app.openapi()["paths"]
    assert paths["/api/v1/finance/settlements"]["get"]["x-crosserp"] == {
        "entity": "Settlement",
        "action": "Settlement.list",
        "permission": "report:read",
        "riskTier": "none",
    }
    assert paths["/api/v1/finance/settlements/{id}"]["get"]["x-crosserp"] == {
        "entity": "Settlement",
        "action": "Settlement.get",
        "permission": "report:read",
        "riskTier": "none",
    }
