"""利润报表 JSON 接口。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import Approval, AuditLog, IamDataScopeRule, ProfitSnapshot, Sku, Store
from crosserp.platform.principal import ActorType, Principal


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _store(name: str, currency: str) -> Store:
    return Store(
        id=uuid4(),
        platform="amazon",
        marketplace="US",
        name=name,
        currency=currency,
    )


def _snapshot(
    store: Store,
    *,
    internal_sku: str,
    period: str,
    revenue: str,
    fees: str = "0",
    refunds: str = "0",
    promotion: str = "0",
    cogs: str = "0",
    freight: str = "0",
    ads: str | None = None,
    profit: str = "0",
    profit_cny: str | None = None,
    fx_rate: str | None = None,
    status: str = "ok",
) -> ProfitSnapshot:
    return ProfitSnapshot(
        id=uuid4(),
        store_id=store.id,
        period=period,
        internal_sku=internal_sku,
        revenue=Decimal(revenue),
        fees=Decimal(fees),
        refunds=Decimal(refunds),
        promotion=Decimal(promotion),
        cogs=Decimal(cogs),
        freight=Decimal(freight),
        ads=None if ads is None else Decimal(ads),
        profit=Decimal(profit),
        currency=store.currency,
        calc_version="profit-v1",
        inputs_hash="b" * 64,
        qty_sold=2,
        qty_refunded=1,
        qty_net=2,
        fx_rate=None if fx_rate is None else Decimal(fx_rate),
        profit_cny=None if profit_cny is None else Decimal(profit_cny),
        ads_included=ads is not None,
        status=status,
        recon_run_id=None,
    )


def _seed(session: Session) -> dict[str, str]:
    user = create_user(
        session,
        username="profit-reader",
        password="Profit-test-password-1",
        roles=(Role.OPERATOR,),
    )
    visible = _store("visible-shop", "USD")
    hidden = _store("hidden-shop", "EUR")
    session.add_all([visible, hidden])
    session.flush()
    session.add(
        Sku(
            store_id=visible.id,
            platform_sku="AMZ-1",
            internal_sku="SKU-1",
            title="杯子",
            active=True,
        )
    )
    session.add_all(
        [
            _snapshot(
                visible,
                internal_sku="SKU-1",
                period="2026-10",
                revenue="12.3456",
                fees="-0.0001",
                refunds="1.0000",
                promotion="0.5000",
                cogs="1.2500",
                freight="2.0000",
                ads="0.2500",
                profit="7.2500",
                profit_cny="50.4000",
                fx_rate="7.2",
            ),
            _snapshot(
                visible,
                internal_sku="SKU-2",
                period="2026-09",
                revenue="3.0000",
                cogs="1.0000",
                profit="2.0000",
            ),
            _snapshot(
                hidden,
                internal_sku="SKU-1",
                period="2026-10",
                revenue="99.0000",
                profit="80.0000",
            ),
            _snapshot(
                hidden,
                internal_sku="SKU-HIDDEN",
                period="2026-10",
                revenue="4.0000",
                profit="1.0000",
            ),
        ]
    )
    session.add(
        IamDataScopeRule(
            name="profit-scope",
            entity="*",
            scope_type="storeIds",
            values=[str(visible.id)],
            updated_by=user.id,
            updated_at=datetime.now(UTC),
        )
    )
    return {"visible": str(visible.id), "hidden": str(hidden.id)}


def test_profit_list_filters_scope_page_and_amount_minor(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        ids = _seed(session)
        before_snapshots = session.scalar(select(func.count()).select_from(ProfitSnapshot))
        before_audit = session.scalar(select(func.count()).select_from(AuditLog))

    _login(json_client, "profit-reader", "Profit-test-password-1")
    listed = json_client.get("/api/v1/finance/profit")
    assert listed.status_code == 200
    body = listed.json()
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["total"] == 2
    assert {item["internalSku"] for item in body["items"]} == {"SKU-1", "SKU-2"}
    assert {item["storeId"] for item in body["items"]} == {ids["visible"]}

    sku1 = next(item for item in body["items"] if item["internalSku"] == "SKU-1")
    assert sku1["name"] == "杯子"
    assert sku1["storeName"] == "visible-shop"
    assert sku1["period"] == "2026-10"
    assert sku1["currency"] == "USD"
    assert sku1["revenue"] == {"amountMinor": 123456, "currency": "USD"}
    assert sku1["fees"] == {"amountMinor": -1, "currency": "USD"}
    assert sku1["refunds"] == {"amountMinor": 10000, "currency": "USD"}
    assert sku1["promotion"] == {"amountMinor": 5000, "currency": "USD"}
    assert sku1["cogs"] == {"amountMinor": 12500, "currency": "USD"}
    assert sku1["freight"] == {"amountMinor": 20000, "currency": "USD"}
    assert sku1["ads"] == {"amountMinor": 2500, "currency": "USD"}
    assert sku1["profit"] == {"amountMinor": 72500, "currency": "USD"}
    assert sku1["profitCny"] == {"amountMinor": 504000, "currency": "CNY"}
    assert isinstance(sku1["fxRate"], str)
    assert Decimal(sku1["fxRate"]) == Decimal("7.2")
    assert sku1["qtySold"] == 2
    assert sku1["qtyNet"] == 2
    assert sku1["status"] == "ok"

    by_period = json_client.get("/api/v1/finance/profit", params={"period": "2026-09"})
    assert by_period.status_code == 200
    assert [item["internalSku"] for item in by_period.json()["items"]] == ["SKU-2"]

    by_sku = json_client.get("/api/v1/finance/profit", params={"sku": "SKU-1"})
    assert [item["internalSku"] for item in by_sku.json()["items"]] == ["SKU-1"]

    by_store = json_client.get("/api/v1/finance/profit", params={"storeId": ids["visible"]})
    assert by_store.json()["total"] == 2
    hidden_store = json_client.get("/api/v1/finance/profit", params={"storeId": ids["hidden"]})
    assert hidden_store.status_code == 200
    assert hidden_store.json()["total"] == 0

    page = json_client.get(
        "/api/v1/finance/profit",
        params={"page": 2, "pageSize": 1, "sort": "internalSku"},
    )
    assert page.json()["total"] == 2
    assert page.json()["page"] == 2
    assert page.json()["pageSize"] == 1
    assert [item["internalSku"] for item in page.json()["items"]] == ["SKU-2"]

    searched = json_client.get("/api/v1/finance/profit", params={"q": "hidden"})
    assert searched.json()["total"] == 0
    found = json_client.get("/api/v1/finance/profit", params={"q": "sku-1"})
    assert [item["internalSku"] for item in found.json()["items"]] == ["SKU-1"]

    invalid = json_client.get(
        "/api/v1/finance/profit", params={"sort": "unknown", "period": "2026-13"}
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "VALIDATION_FAILED"

    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(ProfitSnapshot)) == before_snapshots
        assert session.scalar(select(func.count()).select_from(AuditLog)) == before_audit


def test_profit_requires_login_and_hides_missing_permission(
    json_client: TestClient, api_engine
) -> None:
    anonymous = json_client.get("/api/v1/finance/profit")
    anonymous_sku = json_client.get("/api/v1/finance/profit/sku/SKU-1")
    assert anonymous.status_code == anonymous_sku.status_code == 401
    assert anonymous.json()["code"] == anonymous_sku.json()["code"] == "AUTH_REQUIRED"

    with Session(api_engine) as session, session.begin():
        create_user(session, username="profit-none", password="Profit-test-password-1", roles=())
    _login(json_client, "profit-none", "Profit-test-password-1")
    denied = json_client.get("/api/v1/finance/profit")
    denied_sku = json_client.get("/api/v1/finance/profit/sku/SKU-1")
    assert denied.status_code == denied_sku.status_code == 404
    assert denied.json()["code"] == denied_sku.json()["code"] == "FORBIDDEN"


def test_profit_sku_detail_hides_out_of_scope_and_missing(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        ids = _seed(session)

    _login(json_client, "profit-reader", "Profit-test-password-1")
    detail = json_client.get("/api/v1/finance/profit/sku/SKU-1")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["internalSku"] == "SKU-1"
    assert payload["period"] == "2026-10"
    assert payload["row"]["storeId"] == ids["visible"]
    assert payload["row"]["revenue"]["amountMinor"] == 123456
    assert [item["storeId"] for item in payload["rows"]] == [ids["visible"]]
    assert ids["hidden"] not in {item["storeId"] for item in payload["rows"]}

    scoped = json_client.get(
        "/api/v1/finance/profit/sku/SKU-1",
        params={"storeId": ids["visible"], "period": "2026-10"},
    )
    assert scoped.status_code == 200
    assert scoped.json()["row"]["profit"]["amountMinor"] == 72500

    hidden = json_client.get("/api/v1/finance/profit/sku/SKU-HIDDEN")
    missing = json_client.get("/api/v1/finance/profit/sku/NO-SUCH-SKU")
    hidden_store = json_client.get(
        "/api/v1/finance/profit/sku/SKU-1", params={"storeId": ids["hidden"]}
    )
    assert hidden.status_code == missing.status_code == hidden_store.status_code == 404
    assert hidden.json()["code"] == missing.json()["code"] == "NOT_FOUND"


def test_profit_agent_reads_without_writing(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="profit-agent-user",
            password="Profit-test-password-1",
            roles=(Role.VIEWER,),
        )
        store = _store("agent-shop", "USD")
        session.add(store)
        session.flush()
        session.add(
            _snapshot(
                store,
                internal_sku="SKU-A",
                period="2026-10",
                revenue="1.0000",
                profit="1.0000",
            )
        )
        user_id = user.id
    from crosserp.platform.principal import get_principal

    json_client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user_id,
        actor_type=ActorType.AGENT,
        agent_id="profit-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    response = json_client.get("/api/v1/finance/profit", params={"sku": "SKU-A"})
    assert response.status_code == 200
    assert response.json()["items"][0]["revenue"]["amountMinor"] == 10000
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(Approval)) == 0


def test_missing_amount_serializes_as_null() -> None:
    from crosserp.api.routers.fin_profit import money_payload

    assert money_payload(None, "USD") is None
    assert money_payload(Decimal("12.3456"), "USD") == {"amountMinor": 123456, "currency": "USD"}
    assert money_payload(Decimal("-0.0001"), "EUR") == {"amountMinor": -1, "currency": "EUR"}


def test_profit_route_metadata_matches_contract(json_client: TestClient) -> None:
    paths = json_client.app.openapi()["paths"]
    assert paths["/api/v1/finance/profit"]["get"]["x-crosserp"] == {
        "entity": "ProfitView",
        "action": "ProfitView.list",
        "permission": "report:read",
        "riskTier": "none",
    }
    assert paths["/api/v1/finance/profit/sku/{internalSku}"]["get"]["x-crosserp"] == {
        "entity": "ProfitView",
        "action": "ProfitView.read_sku",
        "permission": "report:read",
        "riskTier": "none",
    }
