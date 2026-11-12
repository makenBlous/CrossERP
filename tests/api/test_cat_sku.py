from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AuditLog,
    Brand,
    Category,
    EntityVersion,
    IamDataScopeRule,
    IamPermissionOverride,
    SkuCost,
    Store,
)
from crosserp.platform.principal import ActorType, Principal, get_principal


def _principal(*permissions: str, agent: bool = False) -> Principal:
    user_id = uuid4()
    return Principal(
        user_id=user_id,
        roles=frozenset(),
        permissions=frozenset(permissions),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="cat-test-agent" if agent else None,
        on_behalf_of=user_id if agent else None,
        channel="mcp" if agent else "web",
    )


def _seed(api_engine) -> tuple[UUID, UUID, UUID]:
    store_id, category_id, brand_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        session.add(
            Store(
                id=store_id,
                platform="amazon",
                marketplace="US",
                name="测试店铺",
                currency="USD",
            )
        )
        session.add(
            Category(
                id=category_id,
                name="电子产品",
                active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Brand(
                id=brand_id,
                name="测试品牌",
                active=True,
                created_at=now,
                updated_at=now,
                provenance={},
            )
        )
        session.add(
            IamDataScopeRule(
                name="sku-test-all-stores",
                entity="*",
                scope_type="all",
                values=[],
                updated_at=now,
            )
        )
    return store_id, category_id, brand_id


def _install(client: TestClient, principal: Principal) -> Principal:
    from crosserp.platform.principal import get_principal

    with Session(client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"sku-{uuid4().hex}",
            password="Sku-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="catalog SKU test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        user_id = user.id
    effective = replace(
        principal,
        user_id=user_id,
        on_behalf_of=user_id if principal.is_agent else None,
    )
    client.app.dependency_overrides[get_principal] = lambda: effective
    return effective


def test_sku_crud_and_lookup(json_client: TestClient, api_engine, monkeypatch) -> None:
    store_id, category_id, brand_id = _seed(api_engine)
    app = json_client.app
    _install(json_client, _principal("item:read", "item:create", "item:write"))
    try:
        response = json_client.post(
            "/api/v1/catalog/skus",
            json={
                "internalSku": "INT-001",
                "platformSku": "AMZ-001",
                "title": "测试商品",
                "storeId": str(store_id),
                "categoryId": str(category_id),
                "brandId": str(brand_id),
                "active": True,
            },
            headers={"Idempotency-Key": "sku-create-1"},
        )
        assert response.status_code == 201
        created = response.json()
        sku_id = created["id"]
        assert created["version"] == 1

        replay = json_client.post(
            "/api/v1/catalog/skus",
            json={
                "internalSku": "INT-001",
                "platformSku": "AMZ-001",
                "title": "测试商品",
                "storeId": str(store_id),
                "categoryId": str(category_id),
                "brandId": str(brand_id),
                "active": True,
            },
            headers={"Idempotency-Key": "sku-create-1"},
        )
        assert replay.status_code == 201
        assert replay.json() == created

        listed = json_client.get(
            "/api/v1/catalog/skus?page=1&pageSize=10&q=INT-001&sort=internalSku"
        )
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["internalSku"] == "INT-001"

        detail = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
        assert detail.status_code == 200
        assert "unitCost" not in detail.json()
        with Session(api_engine) as session, session.begin():
            session.add(
                SkuCost(
                    internal_sku="INT-001",
                    valid_from=datetime.now(UTC),
                    unit_cost=Decimal("1.25"),
                    freight_per_unit=Decimal("0"),
                    currency="USD",
                )
            )
        cost_visible = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
        assert "unitCost" not in cost_visible.json()
        _install(json_client, _principal("item:read", "sku.cost:read"))
        cost_visible = json_client.get(f"/api/v1/catalog/skus/{sku_id}")
        assert cost_visible.json()["unitCost"] == {"amountMinor": 12500, "currency": "USD"}
        _install(json_client, _principal("item:read", "item:create", "item:write"))

        updated = json_client.patch(
            f"/api/v1/catalog/skus/{sku_id}",
            json={"title": "更新商品", "expectedVersion": 1},
            headers={"Idempotency-Key": "sku-update-1"},
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2

        conflict = json_client.patch(
            f"/api/v1/catalog/skus/{sku_id}",
            json={"title": "冲突", "expectedVersion": 1},
            headers={"Idempotency-Key": "sku-update-2"},
        )
        assert conflict.status_code == 409

        status = json_client.post(
            "/api/v1/catalog/skus/status",
            json={"ids": [sku_id], "active": False},
            headers={"Idempotency-Key": "sku-status-1"},
        )
        assert status.status_code == 200
        assert status.json()["updated"] == 1

        lookups = json_client.get("/api/v1/catalog/lookups?page=1&pageSize=50")
        assert lookups.status_code == 200
        kinds = {item["kind"] for item in lookups.json()["items"]}
        assert {"category", "brand", "store", "currency"} <= kinds
    finally:
        app.dependency_overrides.pop(get_principal, None)


def test_sku_forbidden_and_missing_are_404(json_client: TestClient, api_engine) -> None:
    _, _, _ = _seed(api_engine)
    app = json_client.app
    _install(json_client, _principal("report:read"))
    try:
        assert json_client.get("/api/v1/catalog/skus").status_code == 404
        assert json_client.get(f"/api/v1/catalog/skus/{uuid4()}").status_code == 404
    finally:
        app.dependency_overrides.pop(get_principal, None)


def test_agent_medium_action_has_undo_and_audit_context(
    json_client: TestClient, api_engine
) -> None:
    store_id, _, _ = _seed(api_engine)
    principal = _principal("item:create", agent=True)
    app = json_client.app
    principal = _install(json_client, principal)
    try:
        response = json_client.post(
            "/api/v1/catalog/skus",
            json={
                "internalSku": "AGENT-001",
                "platformSku": "AGENT-PLATFORM-001",
                "title": "代理商品",
                "storeId": str(store_id),
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["undo"]["action"] == "Sku.update"
        with Session(api_engine) as session:
            version = session.scalar(
                select(EntityVersion).where(
                    EntityVersion.entity_type == "Sku", EntityVersion.entity_id == body["id"]
                )
            )
            assert version is not None
            assert version.actor_type == "agent"
            assert version.on_behalf_of == principal.on_behalf_of
            assert session.scalar(select(AuditLog).where(AuditLog.id == version.audit_log_id))
    finally:
        app.dependency_overrides.pop(get_principal, None)


def test_sku_invalid_input_returns_validation_error(json_client: TestClient) -> None:
    app = json_client.app
    _install(json_client, _principal("item:create"))
    try:
        response = json_client.post(
            "/api/v1/catalog/skus",
            json={
                "id": str(uuid4()),
                "internalSku": "INVALID-001",
                "platformSku": "INVALID-PLATFORM-001",
                "title": "非法商品",
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"

        missing_platform = json_client.post(
            "/api/v1/catalog/skus",
            json={"internalSku": "INVALID-002", "title": "缺平台 SKU"},
        )
        assert missing_platform.status_code == 422
        assert missing_platform.json()["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_principal, None)
