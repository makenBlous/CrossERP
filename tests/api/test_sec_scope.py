"""店铺数据范围和 SKU 成本字段权限。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    IamDataScopeRule,
    IamPermissionOverride,
    Sku,
    SkuCost,
    Store,
    UserRole,
)
from crosserp.iam.service import IAMService
from crosserp.platform.principal import ActorType, Principal, get_principal


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def _allow(session: Session, user_id: UUID, *permissions: str) -> None:
    now = datetime.now(UTC)
    session.add_all(
        IamPermissionOverride(
            user_id=user_id,
            permission=permission,
            effect="allow",
            reason="sec-scope",
            data_scopes=[],
            created_at=now,
        )
        for permission in permissions
    )


def _store(name: str) -> Store:
    return Store(id=uuid4(), platform="amazon", marketplace="US", name=name, currency="USD")


def _sku(store_id: UUID, internal_sku: str) -> Sku:
    now = datetime.now(UTC)
    return Sku(
        id=uuid4(),
        store_id=store_id,
        platform_sku=internal_sku,
        internal_sku=internal_sku,
        title=internal_sku,
        aliases_json=[],
        active=True,
        created_at=now,
        updated_at=now,
    )


def _rule(
    *,
    name: str,
    entity: str,
    scope_type: str,
    values: object,
    user_id: UUID,
) -> IamDataScopeRule:
    return IamDataScopeRule(
        name=name,
        entity=entity,
        scope_type=scope_type,
        values=values,
        updated_by=user_id,
        updated_at=datetime.now(UTC),
    )


def test_store_scope_hides_other_stores_on_read_and_denies_write(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="scope-a", password="Scope-test-password-123")
        visible = _store("visible")
        hidden = _store("hidden")
        session.add_all([visible, hidden])
        session.flush()
        session.add_all([_sku(visible.id, "SKU-A"), _sku(hidden.id, "SKU-B")])
        session.add(
            _rule(
                name="only-a",
                entity="*",
                scope_type="storeIds",
                values=[str(visible.id)],
                user_id=user.id,
            )
        )
        _allow(session, user.id, "item:read", "item:create", "item:write", "report:read")
        hidden_sku_id = session.scalar(select(Sku.id).where(Sku.internal_sku == "SKU-B"))
        hidden_store_id = hidden.id
    _login(json_client, "scope-a", "Scope-test-password-123")

    listed = json_client.get("/api/v1/catalog/skus")
    detail = json_client.get(f"/api/v1/catalog/skus/{hidden_sku_id}")
    created = json_client.post(
        "/api/v1/catalog/skus",
        json={
            "internalSku": "SKU-NEW",
            "platformSku": "SKU-NEW",
            "title": "越权",
            "storeId": str(hidden_store_id),
        },
    )
    updated = json_client.patch(
        f"/api/v1/catalog/skus/{hidden_sku_id}",
        json={"title": "越权改"},
    )
    stores = json_client.get("/api/v1/stores")

    assert listed.status_code == 200
    assert [item["internalSku"] for item in listed.json()["items"]] == ["SKU-A"]
    assert detail.status_code == 404
    assert detail.json()["code"] == "NOT_FOUND"
    assert created.status_code == 403
    assert created.json()["code"] == "DATA_SCOPE_DENIED"
    assert updated.status_code == 403
    assert updated.json()["code"] == "DATA_SCOPE_DENIED"
    assert [item["name"] for item in stores.json()["items"]] == ["visible"]
    with Session(api_engine) as session:
        assert session.scalar(select(Sku).where(Sku.internal_sku == "SKU-NEW")) is None
        assert session.scalar(select(Sku.title).where(Sku.id == hidden_sku_id)) == "SKU-B"


def test_empty_store_scope_returns_empty_lists_not_all(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="scope-empty",
            password="Scope-test-password-123",
            roles=(Role.OPERATOR,),
        )
        store = _store("should-hide")
        session.add(store)
        session.flush()
        session.add(_sku(store.id, "SKU-HIDDEN"))
        session.add(
            _rule(name="empty", entity="*", scope_type="storeIds", values=[], user_id=user.id)
        )
        _allow(session, user.id, "item:read", "report:read")
    _login(json_client, "scope-empty", "Scope-test-password-123")

    skus = json_client.get("/api/v1/catalog/skus")
    stores = json_client.get("/api/v1/stores")

    assert skus.status_code == 200
    assert skus.json()["items"] == []
    assert skus.json()["total"] == 0
    assert stores.status_code == 200
    assert stores.json()["items"] == []


def test_malformed_store_scope_fails_closed(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="scope-bad",
            password="Scope-test-password-123",
            roles=(Role.OPERATOR,),
        )
        session.add_all([_store("one"), _store("two")])
        session.add(
            _rule(
                name="bad",
                entity="*",
                scope_type="storeIds",
                values=["not-a-uuid"],
                user_id=user.id,
            )
        )
    _login(json_client, "scope-bad", "Scope-test-password-123")

    response = json_client.get("/api/v1/stores")

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert "items" not in response.json()


def test_missing_store_scope_fails_closed(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="scope-missing", password="Scope-test-password-123")
        store = _store("orphan")
        session.add(store)
        session.flush()
        session.add(_sku(store.id, "SKU-ORPHAN"))
        _allow(session, user.id, "item:read")
    _login(json_client, "scope-missing", "Scope-test-password-123")

    response = json_client.get("/api/v1/catalog/skus")

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_FAILED"


def test_sku_cost_follows_iam_field_permission_not_role_name(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        accountant = create_user(session, username="cost-yes", password="Scope-test-password-123")
        finance = create_user(
            session,
            username="cost-finance",
            password="Scope-test-password-123",
            roles=(Role.FINANCE,),
        )
        create_user(
            session, username="cost-admin", password="Scope-test-password-123", roles=(Role.ADMIN,)
        )
        session.add(
            UserRole(user_id=accountant.id, role="accountant", granted_at=datetime.now(UTC))
        )
        _allow(session, accountant.id, "item:read")
        _allow(session, finance.id, "item:read")
        store = _store("cost-store")
        session.add(store)
        session.flush()
        session.add(_sku(store.id, "SKU-COST"))
        session.add(
            SkuCost(
                internal_sku="SKU-COST",
                valid_from=datetime.now(UTC),
                unit_cost=Decimal("1.25"),
                freight_per_unit=Decimal("0.10"),
                currency="USD",
            )
        )
        sku_id = session.scalar(select(Sku.id).where(Sku.internal_sku == "SKU-COST"))
    IAMService(api_engine).update_role(
        "admin",
        permissions={"item:read": "allow", "user:read": "allow", "user:write": "allow"},
    )
    _login(json_client, "cost-yes", "Scope-test-password-123")
    allowed = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
    _login(json_client, "cost-finance", "Scope-test-password-123")
    finance_hidden = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
    _login(json_client, "cost-admin", "Scope-test-password-123")
    admin_hidden = json_client.get(f"/api/v1/catalog/skus/{sku_id}")

    assert allowed.status_code == 200
    assert allowed.json()["unitCost"] == {"amountMinor": 12500, "currency": "USD"}
    assert allowed.json()["freightPerUnit"] == {"amountMinor": 1000, "currency": "USD"}
    assert finance_hidden.status_code == 200
    assert "unitCost" not in finance_hidden.json()
    assert "freightPerUnit" not in finance_hidden.json()
    assert admin_hidden.status_code == 200
    assert "unitCost" not in admin_hidden.json()


def test_revoked_cost_permission_disappears_on_next_request(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="cost-revoke", password="Scope-test-password-123")
        store = _store("revoke-store")
        session.add(store)
        session.flush()
        session.add(_sku(store.id, "SKU-REVOKE"))
        session.add(
            SkuCost(
                internal_sku="SKU-REVOKE",
                valid_from=datetime.now(UTC),
                unit_cost=Decimal("2"),
                freight_per_unit=Decimal("0"),
                currency="USD",
            )
        )
        session.add(
            IamDataScopeRule(
                name="revoke-all",
                entity="*",
                scope_type="all",
                values=[],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        _allow(session, user.id, "item:read", "sku.cost:read")
        user_id = user.id
        sku_id = session.scalar(select(Sku.id).where(Sku.internal_sku == "SKU-REVOKE"))
    _login(json_client, "cost-revoke", "Scope-test-password-123")
    before = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
    IAMService(api_engine).set_override(user_id, "sku.cost:read", effect="deny", reason="收回")
    after = json_client.get(f"/api/v1/catalog/skus/{sku_id}")

    assert before.status_code == 200
    assert before.json()["unitCost"]["amountMinor"] == 20000
    assert after.status_code == 200
    assert "unitCost" not in after.json()


def test_agent_cost_follows_represented_user_not_snapshot(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="cost-agent", password="Scope-test-password-123")
        store = _store("agent-store")
        session.add(store)
        session.flush()
        session.add(_sku(store.id, "SKU-AGENT"))
        session.add(
            SkuCost(
                internal_sku="SKU-AGENT",
                valid_from=datetime.now(UTC),
                unit_cost=Decimal("3"),
                freight_per_unit=Decimal("0"),
                currency="USD",
            )
        )
        session.add(
            IamDataScopeRule(
                name="agent-all",
                entity="*",
                scope_type="all",
                values=[],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        _allow(session, user.id, "item:read")
        user_id = user.id
        sku_id = session.scalar(select(Sku.id).where(Sku.internal_sku == "SKU-AGENT"))
    json_client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user_id,
        roles=frozenset({"admin", "finance"}),
        permissions=frozenset({"item:read", "sku.cost:read", "item:cost:read", "cost:read"}),
        actor_type=ActorType.AGENT,
        agent_id="sec-scope-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    try:
        response = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
    finally:
        json_client.app.dependency_overrides.pop(get_principal, None)

    assert response.status_code == 200
    assert "unitCost" not in response.json()
    assert "freightPerUnit" not in response.json()
