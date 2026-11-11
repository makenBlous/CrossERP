from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.db.schema import ActionExecution, AuditLog, Brand, EntityEvent, EntityVersion
from crosserp.db.session import sqlite_file_url
from crosserp.platform.principal import ActorType, Principal, get_principal
from crosserp.web.app import create_app


@pytest.fixture
def brand_client(tmp_path: Path) -> Iterator[tuple[TestClient, object, Principal]]:
    database_url = sqlite_file_url(tmp_path / "brand.db")
    app = create_app(database_url)
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"brand:read", "brand:create", "brand:write"}),
    )
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        yield client, app.state.database_engine, principal
    app.state.database_engine.dispose()


def test_brand_list_is_paginated_searchable_and_sorted(brand_client) -> None:
    client, engine, _ = brand_client
    with Session(engine) as session, session.begin():
        session.add_all([Brand(name="Zeta", active=True), Brand(name="Alpha", active=True)])

    response = client.get("/api/v1/catalog/brands?page=1&pageSize=1&q=a&sort=name")

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Alpha"
    assert response.json()["total"] == 2
    assert response.json()["pageSize"] == 1


def test_brand_create_writes_action_version_audit_and_undo(brand_client) -> None:
    client, engine, principal = brand_client
    response = client.post(
        "/api/v1/catalog/brands",
        json={"name": "Acme"},
        headers={"Idempotency-Key": "brand-create-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["version"] == 1
    assert body["undo"]["action"] == "Brand.status"
    brand_id = UUID(body["id"])
    with Session(engine) as session:
        brand = session.get(Brand, brand_id)
        assert brand is not None and brand.name == "Acme" and brand.active is True
        version = session.scalar(
            select(EntityVersion).where(EntityVersion.entity_id == str(brand_id))
        )
        audit = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()))
        assert version is not None and version.actor_type == "human"
        assert version.action_id == "Brand.create"
        assert audit is not None
        assert audit.actor_type == "user"
        assert session.scalar(select(func.count()).select_from(EntityEvent)) == 2
        assert principal.user_id == version.actor_id


def test_brand_write_is_idempotent_and_expected_version_conflicts(brand_client) -> None:
    client, engine, _ = brand_client
    first = client.post(
        "/api/v1/catalog/brands",
        json={"name": "Acme"},
        headers={"Idempotency-Key": "brand-create-2"},
    )
    brand_id = first.json()["id"]
    replay = client.post(
        "/api/v1/catalog/brands",
        json={"name": "Acme"},
        headers={"Idempotency-Key": "brand-create-2"},
    )
    assert replay.status_code == 201
    assert replay.json() == first.json()

    updated = client.patch(
        f"/api/v1/catalog/brands/{brand_id}",
        json={"name": "Acme 2", "expectedVersion": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    conflict = client.patch(
        f"/api/v1/catalog/brands/{brand_id}",
        json={"name": "Acme 3", "expectedVersion": 1},
    )
    assert conflict.status_code == 409
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Brand)) == 1


def test_brand_status_and_missing_resources(brand_client) -> None:
    client, _, _ = brand_client
    created = client.post(
        "/api/v1/catalog/brands", json={"name": "Acme"}, headers={"Idempotency-Key": "brand-3"}
    )
    brand_id = created.json()["id"]
    changed = client.post(
        "/api/v1/catalog/brands/status",
        json={"id": brand_id, "status": "inactive", "expectedVersion": 1},
        headers={"Idempotency-Key": "brand-status-1"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "succeeded"
    assert (
        client.patch("/api/v1/catalog/brands/does-not-exist", json={"name": "x"}).status_code == 404
    )
    assert (
        client.post(
            "/api/v1/catalog/brands/status",
            json={"id": "does-not-exist", "status": "active"},
            headers={"Idempotency-Key": "brand-status-404"},
        ).status_code
        == 404
    )


def test_brand_permission_and_agent_medium_behavior(brand_client) -> None:
    client, engine, _ = brand_client
    from crosserp.web.app import create_app

    denied_app = create_app(sqlite_file_url(Path(engine.url.database)))
    denied_app.dependency_overrides[get_principal] = lambda: Principal(user_id=uuid4())
    with TestClient(denied_app) as denied:
        assert denied.get("/api/v1/catalog/brands").status_code == 404
        assert denied.post("/api/v1/catalog/brands", json={"name": "x"}).status_code == 404
    denied_app.state.database_engine.dispose()

    agent = Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
        permissions=frozenset({"brand:create", "brand:read", "brand:write"}),
        channel="mcp",
    )
    client.app.dependency_overrides[get_principal] = lambda: agent
    response = client.post(
        "/api/v1/catalog/brands",
        json={"name": "Agent brand"},
        headers={"Idempotency-Key": "agent-brand"},
    )
    assert response.status_code == 201
    with Session(engine) as session:
        version = session.scalar(
            select(EntityVersion).where(EntityVersion.action_id == "Brand.create")
        )
        execution = session.scalar(
            select(ActionExecution).where(ActionExecution.action_id == "Brand.create")
        )
        assert (
            version is not None
            and version.actor_type == "agent"
            and version.on_behalf_of == agent.on_behalf_of
        )
        assert execution is not None and execution.result_json["undo"]


def test_brand_routes_publish_contract_metadata_and_reads_do_not_audit(brand_client) -> None:
    client, engine, _ = brand_client
    paths = client.app.openapi()["paths"]
    expected = {
        "/api/v1/catalog/brands": ("Brand.list", "brand:read", "none"),
        "/api/v1/catalog/brands/{id}": ("Brand.update", "brand:write", "medium"),
        "/api/v1/catalog/brands/status": ("Brand.status", "brand:write", "medium"),
    }
    assert set(paths["/api/v1/catalog/brands"]) == {"get", "post"}
    for path, (action, permission, risk_tier) in expected.items():
        method = "patch" if path.endswith("{id}") else "post" if path.endswith("status") else "get"
        metadata = paths[path][method]["x-crosserp"]
        assert (metadata["action"], metadata["permission"], metadata["riskTier"]) == (
            action,
            permission,
            risk_tier,
        )
    assert client.get("/api/v1/catalog/brands").status_code == 200
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AuditLog)) == 0
