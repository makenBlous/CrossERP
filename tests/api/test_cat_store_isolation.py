"""各 catalog 模块只按 IAM 店铺范围返回数据。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    Bundle,
    IamDataScopeRule,
    IamPermissionOverride,
    Listing,
    Sku,
    SkuCost,
    SkuMapping,
    Store,
)


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
            reason="store isolation",
            data_scopes=[],
            created_at=now,
        )
        for permission in permissions
    )


def _stores(session: Session, user_id: UUID) -> tuple[Store, Store]:
    visible = Store(id=uuid4(), platform="amazon", marketplace="US", name="visible", currency="USD")
    hidden = Store(id=uuid4(), platform="amazon", marketplace="DE", name="hidden", currency="EUR")
    session.add_all([visible, hidden])
    session.flush()
    session.add(
        IamDataScopeRule(
            name="only-visible",
            entity="*",
            scope_type="storeIds",
            values=[str(visible.id)],
            updated_by=user_id,
            updated_at=datetime.now(UTC),
        )
    )
    return visible, hidden


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


def test_listing_user_cannot_see_other_store(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="list-scope", password="Scope-test-password-123")
        visible, hidden = _stores(session, user.id)
        session.add_all(
            [
                Listing(
                    id=uuid4(),
                    store_id=visible.id,
                    platform_sku="LIST-A",
                    price=Decimal("1.0000"),
                    currency="USD",
                    status="active",
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
                Listing(
                    id=uuid4(),
                    store_id=hidden.id,
                    platform_sku="LIST-B",
                    price=Decimal("2.0000"),
                    currency="EUR",
                    status="active",
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        _allow(session, user.id, "listing:read")
    _login(json_client, "list-scope", "Scope-test-password-123")

    response = json_client.get("/api/v1/catalog/listings")

    assert response.status_code == 200
    assert {item["platformSku"] for item in response.json()["items"]} == {"LIST-A"}


def test_mapping_user_cannot_see_other_store(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="map-scope", password="Scope-test-password-123")
        visible, hidden = _stores(session, user.id)
        session.add_all(
            [
                SkuMapping(
                    id=uuid4(),
                    store_id=visible.id,
                    platform_sku="MAP-A",
                    internal_sku="SKU-A",
                    confidence="high",
                    source="human",
                    state="confirmed",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    provenance_json={},
                ),
                SkuMapping(
                    id=uuid4(),
                    store_id=hidden.id,
                    platform_sku="MAP-B",
                    internal_sku="SKU-B",
                    confidence="high",
                    source="human",
                    state="confirmed",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    provenance_json={},
                ),
            ]
        )
        _allow(session, user.id, "listing:read")
    _login(json_client, "map-scope", "Scope-test-password-123")

    response = json_client.get("/api/v1/catalog/mappings")

    assert response.status_code == 200
    assert {item["platformSku"] for item in response.json()["items"]} == {"MAP-A"}


def test_cost_user_cannot_see_other_store(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="cost-scope", password="Scope-test-password-123")
        visible, hidden = _stores(session, user.id)
        session.add_all([_sku(visible.id, "COST-A"), _sku(hidden.id, "COST-B")])
        session.add_all(
            [
                SkuCost(
                    id=uuid4(),
                    internal_sku="COST-A",
                    valid_from=now,
                    unit_cost=Decimal("1.0000"),
                    currency="CNY",
                    freight_per_unit=Decimal("0.0000"),
                    period="2026-11",
                    source="manual",
                    status="effective",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    provenance_json={},
                ),
                SkuCost(
                    id=uuid4(),
                    internal_sku="COST-B",
                    valid_from=now,
                    unit_cost=Decimal("2.0000"),
                    currency="CNY",
                    freight_per_unit=Decimal("0.0000"),
                    period="2026-11",
                    source="manual",
                    status="effective",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    provenance_json={},
                ),
            ]
        )
        _allow(session, user.id, "item:read")
    _login(json_client, "cost-scope", "Scope-test-password-123")

    response = json_client.get("/api/v1/catalog/costs")

    assert response.status_code == 200
    assert {item["internalSku"] for item in response.json()["items"]} == {"COST-A"}


def test_bundle_user_cannot_see_other_store(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="bundle-scope", password="Scope-test-password-123")
        visible, hidden = _stores(session, user.id)
        session.add_all([_sku(visible.id, "BND-A"), _sku(hidden.id, "BND-B")])
        session.add_all(
            [
                Bundle(
                    id=uuid4(),
                    bundle_sku="BUNDLE-A",
                    components_json=[{"internalSku": "BND-A", "qty": 1}],
                    active=True,
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
                Bundle(
                    id=uuid4(),
                    bundle_sku="BUNDLE-B",
                    components_json=[{"internalSku": "BND-B", "qty": 1}],
                    active=True,
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        _allow(session, user.id, "item:read")
    _login(json_client, "bundle-scope", "Scope-test-password-123")

    response = json_client.get("/api/v1/catalog/bundles")

    assert response.status_code == 200
    assert {item["bundleSku"] for item in response.json()["items"]} == {"BUNDLE-A"}
