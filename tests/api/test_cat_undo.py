"""目录中风险动作撤销成功, 并重新校验写权限和店铺范围。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import IamDataScopeRule, IamPermissionOverride, Listing, Store
from crosserp.platform.principal import Principal, get_principal
from crosserp.web.app import create_app


def _user(app, username: str, permissions: tuple[str, ...], store_ids: list[str]) -> Principal:
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(session, username=username, password="Undo-test-password-123")
        now = datetime.now(UTC)
        session.add_all(
            IamPermissionOverride(
                user_id=user.id,
                permission=permission,
                effect="allow",
                reason="undo test",
                data_scopes=[],
                created_at=now,
            )
            for permission in permissions
        )
        session.add(
            IamDataScopeRule(
                name=f"{username}-stores",
                entity="*",
                scope_type="all" if not store_ids else "storeIds",
                values=store_ids,
                updated_by=user.id,
                updated_at=now,
            )
        )
        return Principal(user_id=user.id, permissions=frozenset(permissions))


def test_brand_update_undo_restores_previous_name(api_database: str) -> None:
    app = create_app(api_database)
    principal = _user(
        app,
        "undo-brand",
        ("brand:create", "brand:write", "brand:read", "agent_suggestion:create"),
        [],
    )
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        created = client.post("/api/v1/catalog/brands", json={"name": "旧名"})
        assert created.status_code == 201, created.text
        brand_id = created.json()["id"]
        updated = client.patch(
            f"/api/v1/catalog/brands/{brand_id}",
            json={"name": "新名", "expectedVersion": 1},
            headers={"Idempotency-Key": "brand-undo-update"},
        )
        assert updated.status_code == 200, updated.text
        undo_id = updated.json()["undoId"]
        undone = client.post(f"/api/v1/agent/suggestions/{undo_id}/undo")
        assert undone.status_code == 200, undone.text
        listed = client.get("/api/v1/catalog/brands")
    assert listed.json()["items"][0]["name"] == "旧名"


def test_undo_rechecks_store_scope(api_database: str) -> None:
    app = create_app(api_database)
    writer = _user(
        app,
        "undo-writer",
        ("listing:create", "listing:write", "listing:read", "agent_suggestion:create"),
        [],
    )
    app.dependency_overrides[get_principal] = lambda: writer
    with TestClient(app) as client:
        with Session(app.state.database_engine) as session, session.begin():
            store_a = Store(
                id=uuid4(), platform="amazon", marketplace="US", name="A", currency="USD"
            )
            store_b = Store(
                id=uuid4(), platform="amazon", marketplace="DE", name="B", currency="EUR"
            )
            session.add_all([store_a, store_b])
            store_b_id = str(store_b.id)
            store_a_id = str(store_a.id)
        created = client.post(
            "/api/v1/catalog/listings",
            json={
                "storeId": store_b_id,
                "platformSku": "UNDO-B",
                "price": {"amountMinor": 100, "currency": "EUR"},
            },
            headers={"Idempotency-Key": "listing-undo-create"},
        )
        assert created.status_code == 201, created.text
        listing_id = created.json()["id"]
        updated = client.patch(
            f"/api/v1/catalog/listings/{listing_id}",
            json={"status": "inactive", "expectedVersion": 1},
            headers={"Idempotency-Key": "listing-undo-update"},
        )
        assert updated.status_code == 200, updated.text
        undo_id = updated.json()["undoId"]
        with Session(app.state.database_engine) as session, session.begin():
            rule = session.scalar(select(IamDataScopeRule))
            assert rule is not None
            rule.scope_type = "storeIds"
            rule.values = [store_a_id]
        denied = client.post(f"/api/v1/agent/suggestions/{undo_id}/undo")
    assert denied.status_code == 403
    assert denied.json()["code"] == "DATA_SCOPE_DENIED"
    with Session(app.state.database_engine) as session:
        row = session.get(Listing, UUID(listing_id))
        assert row is not None and row.status == "inactive"
