from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api import install_api
from crosserp.db.migrate import upgrade_head
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AuditLog,
    EntityEvent,
    EntityVersion,
    IamDataScopeRule,
    IamPermissionOverride,
    Store,
)
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import ActorType, Principal, get_principal


def _app(tmp_path: Path) -> tuple[FastAPI, object, UUID]:
    url = sqlite_file_url(tmp_path / "listing.db")
    upgrade_head(url)
    engine = make_engine(url)
    store = Store(id=uuid4(), platform="amazon", marketplace="US", name="demo", currency="USD")
    store_id = store.id
    with Session(engine) as session, session.begin():
        session.add(store)
    app = FastAPI()
    app.state.permission_service = DefaultPermissionService()
    install_api(app, engine)
    return app, engine, store_id


def _install(app: FastAPI, principal: Principal, store_ids: list[UUID]) -> Principal:
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"listing-{uuid4().hex}",
            password="Listing-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="listing test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        session.add(
            IamDataScopeRule(
                id=uuid4(),
                name="listing test scope",
                entity="Listing",
                scope_type="storeIds",
                values=[str(store_id) for store_id in store_ids],
                updated_at=datetime.now(UTC),
            )
        )
        user_id = user.id
    effective = replace(
        principal,
        user_id=user_id,
        on_behalf_of=user_id if principal.is_agent else None,
    )
    app.dependency_overrides[get_principal] = lambda: effective
    return effective


def test_listing_crud_scope_pagination_idempotency_version_and_audit(tmp_path: Path) -> None:
    app, engine, store_id = _app(tmp_path)
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"listing:read", "listing:create", "listing:write"}),
        data_scope={"store_ids": [str(store_id)]},
    )
    # FastAPI dependency overrides need the actual callable as key.
    principal = _install(app, principal, [store_id])
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/catalog/listings",
            headers={"Idempotency-Key": "listing-create-1"},
            json={
                "storeId": str(store_id),
                "platformSku": "SKU-001",
                "asin": "ASIN-001",
                "price": {"amountMinor": 12345, "currency": "USD"},
            },
        )
        assert first.status_code == 201, first.text
        listing = first.json()
        assert listing["status"] == "active"
        assert listing["version"] == 1
        assert listing["undoPayload"]["action"] == "Listing.update"
        replay = client.post(
            "/api/v1/catalog/listings",
            headers={"Idempotency-Key": "listing-create-1"},
            json={
                "storeId": str(store_id),
                "platformSku": "SKU-001",
                "asin": "ASIN-001",
                "price": {"amountMinor": 12345, "currency": "USD"},
            },
        )
        assert replay.status_code == 201
        assert replay.json() == listing

        second = client.post(
            "/api/v1/catalog/listings",
            headers={"Idempotency-Key": "listing-create-2"},
            json={
                "storeId": str(store_id),
                "platformSku": "SKU-002",
                "price": {"amountMinor": 20000, "currency": "USD"},
            },
        )
        assert second.status_code == 201
        listing2 = second.json()

        page = client.get("/api/v1/catalog/listings?page=1&pageSize=1&q=SKU&sort=-platformSku")
        assert page.status_code == 200
        assert page.json()["total"] == 2
        assert len(page.json()["items"]) == 1
        assert page.json()["items"][0]["platformSku"] == "SKU-002"

        detail = client.get(f"/api/v1/catalog/listings/{listing['id']}")
        assert detail.status_code == 200
        assert detail.json()["id"] == listing["id"]

        updated = client.patch(
            f"/api/v1/catalog/listings/{listing['id']}",
            headers={"Idempotency-Key": "listing-update-1"},
            json={"status": "inactive", "expectedVersion": 1},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "inactive"
        assert updated.json()["version"] == 2
        updated_replay = client.patch(
            f"/api/v1/catalog/listings/{listing['id']}",
            headers={"Idempotency-Key": "listing-update-1"},
            json={"status": "inactive", "expectedVersion": 1},
        )
        assert updated_replay.status_code == 200
        assert updated_replay.json() == updated.json()
        conflict = client.patch(
            f"/api/v1/catalog/listings/{listing['id']}",
            headers={"Idempotency-Key": "listing-update-2"},
            json={"status": "active", "expectedVersion": 1},
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "CONFLICT_VERSION"

        listing2_update = client.patch(
            f"/api/v1/catalog/listings/{listing2['id']}",
            headers={"Idempotency-Key": "listing-update-2"},
            json={"status": "inactive", "expectedVersion": 1},
        )
        assert listing2_update.status_code == 200
        assert listing2_update.json()["version"] == 2

        batch = client.post(
            "/api/v1/catalog/listings/status",
            headers={"Idempotency-Key": "listing-status-1"},
            json={
                "ids": [listing["id"], listing2["id"]],
                "status": "active",
                "expectedVersion": 2,
            },
        )
        assert batch.status_code == 200, batch.text
        assert batch.json()["updated"] == 2
        batch_replay = client.post(
            "/api/v1/catalog/listings/status",
            headers={"Idempotency-Key": "listing-status-1"},
            json={
                "ids": [listing["id"], listing2["id"]],
                "status": "active",
                "expectedVersion": 2,
            },
        )
        assert batch_replay.status_code == 200
        assert batch_replay.json() == batch.json()

        assert client.get(f"/api/v1/catalog/listings/{uuid4()}").status_code == 404
    with Session(engine) as session:
        versions = list(
            session.scalars(select(EntityVersion).where(EntityVersion.entity_type == "Listing"))
        )
        audits = list(session.scalars(select(AuditLog).where(AuditLog.action.like("Listing.%"))))
        events = list(
            session.scalars(select(EntityEvent).where(EntityEvent.entity_type == "Listing"))
        )
        assert len(versions) >= 4
        assert all(row.actor_type == "human" for row in versions)
        assert all(row.on_behalf_of is None for row in versions)
        assert audits
        assert events
    engine.dispose()


def test_listing_agent_medium_action_has_undo_and_audit_context(tmp_path: Path) -> None:
    app, engine, store_id = _app(tmp_path)
    agent = Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="agent-listing",
        on_behalf_of=uuid4(),
        delegation_id="delegation-listing",
        permissions=frozenset({"listing:create"}),
        data_scope={"store_ids": [str(store_id)]},
    )
    agent = _install(app, agent, [store_id])
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/listings",
            headers={
                "Idempotency-Key": "agent-listing-create",
                "X-Request-ID": "listing-agent-request",
                "X-Tool-Call-ID": "listing-tool-call",
            },
            json={
                "storeId": str(store_id),
                "platformSku": "AGENT-SKU",
                "price": {"amountMinor": 100, "currency": "USD"},
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["undoPayload"]["action"] == "Listing.update"
    with Session(engine) as session:
        version = session.scalar(
            select(EntityVersion).where(EntityVersion.entity_type == "Listing")
        )
        assert version is not None
        assert version.actor_type == "agent"
        assert version.on_behalf_of == agent.on_behalf_of
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "Listing.create"))
        assert audit is not None
        assert audit.actor_type == "agent"
        assert audit.request_id == "listing-agent-request"
        assert audit.after_json["tool_call_id"] == "listing-tool-call"
    engine.dispose()


def test_listing_scope_denial_is_403_for_write_and_404_for_read(tmp_path: Path) -> None:
    app, engine, store_id = _app(tmp_path)
    denied_store = uuid4()
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"listing:read", "listing:create", "listing:write"}),
        data_scope={"store_ids": [str(denied_store)]},
    )
    _install(app, principal, [denied_store])
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/listings",
            headers={"Idempotency-Key": "scope-denied"},
            json={
                "storeId": str(store_id),
                "platformSku": "DENIED",
                "price": {"amountMinor": 100, "currency": "USD"},
            },
        )
        assert response.status_code == 403
        assert response.json()["code"] == "DATA_SCOPE_DENIED"
        assert client.get("/api/v1/catalog/listings").status_code == 200
        assert client.get(f"/api/v1/catalog/listings/{uuid4()}").status_code == 404
    engine.dispose()


def test_listing_unauthorized_is_404(tmp_path: Path) -> None:
    app, engine, store_id = _app(tmp_path)
    app.dependency_overrides[get_principal] = lambda: Principal(user_id=uuid4())
    with TestClient(app) as client:
        assert client.get("/api/v1/catalog/listings").status_code == 404
        assert client.get(f"/api/v1/catalog/listings/{uuid4()}").status_code == 404
        response = client.post(
            "/api/v1/catalog/listings",
            headers={"Idempotency-Key": "unauthorized-listing"},
            json={
                "storeId": str(store_id),
                "platformSku": "DENIED",
                "price": {"amountMinor": 100, "currency": "USD"},
            },
        )
        assert response.status_code == 404
    engine.dispose()


def test_listing_invalid_request_body_returns_validation_error(tmp_path: Path) -> None:
    app, engine, store_id = _app(tmp_path)

    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"listing:create"}),
        data_scope={"store_ids": [str(store_id)]},
    )
    _install(app, principal, [store_id])
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/listings",
            json={
                "storeId": "not-a-uuid",
                "platformSku": "INVALID",
                "price": {"amountMinor": 100, "currency": "USD"},
            },
        )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    engine.dispose()
