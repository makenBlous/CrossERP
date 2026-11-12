"""幂等回放必须晚于身份和权限, 并且按调用人隔离."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import ActionExecution, Brand, UserRole
from crosserp.db.session import sqlite_file_url
from crosserp.platform.principal import ActorType, Principal, get_principal
from crosserp.web.app import create_app


@pytest.fixture
def idem_app(tmp_path: Path) -> Iterator[tuple[TestClient, object]]:
    app = create_app(sqlite_file_url(tmp_path / "idem.db"))
    with TestClient(app) as client:
        yield client, app.state.database_engine
    app.state.database_engine.dispose()


def _user(engine: object, role: str) -> Principal:
    with Session(engine) as session, session.begin():
        user = create_user(
            session,
            username=f"idem-{uuid4().hex[:10]}",
            password="Idem-test-password-123",
        )
        grant_role(session, user.id, role)
        return Principal(user_id=user.id, roles=frozenset({role}))


def _as(client: TestClient, principal: Principal) -> None:
    client.app.dependency_overrides[get_principal] = lambda: principal


def test_idempotency_is_isolated_by_caller_and_checked_after_auth(idem_app) -> None:
    client, engine = idem_app
    owner = _user(engine, "admin")
    outsider = _user(engine, "viewer")
    peer = _user(engine, "admin")
    body = {"name": "Isolated"}
    headers = {"Idempotency-Key": "shared-key"}

    _as(client, owner)
    created = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert created.status_code == 201
    created_body = created.json()

    client.app.dependency_overrides.clear()
    anonymous = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert anonymous.status_code == 401
    assert anonymous.json() != created_body

    _as(client, outsider)
    denied = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert denied.status_code == 404
    assert denied.json() != created_body

    _as(client, peer)
    peer_write = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert peer_write.status_code == 201
    assert peer_write.json()["id"] != created_body["id"]
    assert peer_write.json() != created_body

    _as(client, owner)
    other_path = client.post("/api/v1/catalog/categories", json=body, headers=headers)
    assert other_path.json() != created_body

    replay = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert replay.status_code == 201
    assert replay.json() == created_body
    conflict = client.post(
        "/api/v1/catalog/brands",
        json={"name": "Different"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    with Session(engine) as session, session.begin():
        session.execute(delete(UserRole).where(UserRole.user_id == owner.user_id))
    revoked = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert revoked.status_code == 404
    assert revoked.json() != created_body
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Brand)) == 2

    agent = Principal(
        user_id=peer.user_id,
        actor_type=ActorType.AGENT,
        agent_id="idem-agent",
        on_behalf_of=peer.user_id,
        channel="mcp",
    )
    _as(client, agent)
    agent_write = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert agent_write.status_code == 201
    assert agent_write.json()["id"] != peer_write.json()["id"]
    _as(client, peer)
    peer_replay = client.post("/api/v1/catalog/brands", json=body, headers=headers)
    assert peer_replay.status_code == 201
    assert peer_replay.json() == peer_write.json()
    with Session(engine) as session:
        rows = list(session.scalars(select(ActionExecution)))
    identities = {row.caller_identity for row in rows if row.idempotency_key == "shared-key"}
    assert len(identities) >= 2
    assert any(item is not None and "idem-agent" in item for item in identities)
