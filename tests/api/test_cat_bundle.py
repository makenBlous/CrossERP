from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, Bundle, EntityVersion, IamPermissionOverride
from crosserp.platform.principal import ActorType, Principal, get_principal
from crosserp.web.app import create_app


@pytest.fixture
def bundle_client(api_database: str) -> Iterator[tuple[TestClient, object]]:
    app = create_app(api_database)
    principal = Principal(
        user_id=uuid4(), permissions=frozenset({"item:read", "item:write", "item:delete"})
    )
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"bundle-{uuid4().hex}",
            password="Bundle-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="bundle test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        principal = replace(principal, user_id=user.id)
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        yield client, principal


def test_bundle_create_list_update_and_deactivate(bundle_client, api_engine) -> None:
    client, _principal = bundle_client
    created = client.post(
        "/api/v1/catalog/bundles",
        json={"bundleSku": "BUNDLE-1", "components": [{"internalSku": "SKU-1", "qty": 2}]},
        headers={"Idempotency-Key": "bundle-create-1"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["bundleSku"] == "BUNDLE-1"
    assert body["version"] == 1
    bundle_id = body["id"]

    listed = client.get("/api/v1/catalog/bundles?page=1&pageSize=10&q=BUNDLE")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/catalog/bundles/{bundle_id}",
        json={"expectedVersion": 1, "components": [{"internalSku": "SKU-1", "qty": 3}]},
        headers={"Idempotency-Key": "bundle-update-1"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    update_replay = client.patch(
        f"/api/v1/catalog/bundles/{bundle_id}",
        json={"expectedVersion": 1, "components": [{"internalSku": "SKU-1", "qty": 3}]},
        headers={"Idempotency-Key": "bundle-update-1"},
    )
    assert update_replay.status_code == 200
    assert update_replay.json() == updated.json()

    conflict = client.patch(
        f"/api/v1/catalog/bundles/{bundle_id}",
        json={"expectedVersion": 1, "bundleSku": "BUNDLE-2"},
    )
    assert conflict.status_code == 409

    deactivated = client.post(
        "/api/v1/catalog/bundles/deactivate",
        json={"ids": [bundle_id], "expectedVersion": 2},
        headers={"Idempotency-Key": "bundle-deactivate-1"},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "deactivated"

    with Session(api_engine) as session:
        row = session.get(Bundle, UUID(bundle_id))
        assert row is not None and row.active is False
        assert session.scalar(select(EntityVersion).where(EntityVersion.entity_id == bundle_id))
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "Bundle.deactivate"))
        assert audit is not None and audit.actor_type == "human"


def test_bundle_idempotent_replay_and_not_found_are_safe(bundle_client) -> None:
    client, _principal = bundle_client
    payload = {"bundleSku": "BUNDLE-REPLAY", "components": []}
    first = client.post(
        "/api/v1/catalog/bundles",
        json=payload,
        headers={"Idempotency-Key": "bundle-replay"},
    )
    replay = client.post(
        "/api/v1/catalog/bundles",
        json=payload,
        headers={"Idempotency-Key": "bundle-replay"},
    )
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    mismatch = client.post(
        "/api/v1/catalog/bundles",
        json={"bundleSku": "OTHER", "components": []},
        headers={"Idempotency-Key": "bundle-replay"},
    )
    assert mismatch.status_code == 409
    assert (
        client.patch(
            f"/api/v1/catalog/bundles/{uuid4()}",
            json={"expectedVersion": 1, "bundleSku": "missing"},
        ).status_code
        == 404
    )
    assert (
        client.patch(f"/api/v1/catalog/bundles/{uuid4()}", json={"expectedVersion": 1}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/catalog/bundles/deactivate",
            json={"ids": [str(uuid4())], "expectedVersion": 1},
            headers={"Idempotency-Key": "bundle-missing-deactivate"},
        ).status_code
        == 404
    )


def test_bundle_medium_ai_executes_and_critical_deactivate_is_rejected(bundle_client) -> None:
    client, principal = bundle_client
    principal = Principal(
        user_id=principal.user_id,
        actor_type=ActorType.AGENT,
        agent_id="bundle-agent",
        on_behalf_of=principal.user_id,
        permissions=frozenset({"item:write", "item:read", "item:delete"}),
    )
    with Session(client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"bundle-agent-{uuid4().hex}",
            password="Bundle-agent-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="bundle agent test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        user_id = user.id
    principal = replace(principal, user_id=user_id, on_behalf_of=user_id)
    client.app.dependency_overrides[get_principal] = lambda: principal
    created = client.post(
        "/api/v1/catalog/bundles",
        json={"bundleSku": "AI-BUNDLE", "components": []},
        headers={"Idempotency-Key": "ai-bundle-create"},
    )
    assert created.status_code == 201
    with Session(bundle_client[0].app.state.database_engine) as session:
        version = session.scalar(
            select(EntityVersion).where(EntityVersion.entity_id == created.json()["id"])
        )
        assert version is not None
        assert version.actor_type == "agent"
        assert version.on_behalf_of == principal.user_id
    denied = client.post(
        "/api/v1/catalog/bundles/deactivate",
        json={"ids": [created.json()["id"]], "expectedVersion": 1},
        headers={"Idempotency-Key": "ai-bundle-deactivate"},
    )
    assert denied.status_code == 403


def test_bundle_permission_denied_is_404(bundle_client) -> None:
    client, _principal = bundle_client
    client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=uuid4(), permissions=frozenset()
    )
    assert client.get("/api/v1/catalog/bundles").status_code == 404
    assert (
        client.post(
            "/api/v1/catalog/bundles",
            json={"bundleSku": "DENIED", "components": []},
            headers={"Idempotency-Key": "bundle-denied"},
        ).status_code
        == 404
    )
