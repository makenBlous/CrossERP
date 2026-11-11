from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import AuditLog, EntityVersion
from crosserp.platform.principal import ActorType, Principal


def _principal(*permissions: str, agent: bool = False) -> Principal:
    user_id = uuid4()
    return Principal(
        user_id=user_id,
        permissions=frozenset(permissions),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="category-agent" if agent else None,
        on_behalf_of=user_id if agent else None,
        channel="mcp" if agent else "web",
    )


def _override(client: TestClient, principal: Principal) -> None:
    from crosserp.platform.principal import get_principal

    client.app.dependency_overrides[get_principal] = lambda: principal


def test_category_crud_tree_pagination_and_idempotency(
    json_client: TestClient,
) -> None:
    _override(json_client, _principal("item_group:read", "item_group:create", "item_group:write"))

    created = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "根类目"},
        headers={"Idempotency-Key": "category-create-1"},
    )
    assert created.status_code == 201
    root = created.json()
    assert root["version"] == 1
    assert root["undo"]["action"] == "Category.delete"

    replay = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "根类目"},
        headers={"Idempotency-Key": "category-create-1"},
    )
    assert replay.status_code == 201
    assert replay.json() == root

    child = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "子类目", "parentId": root["id"]},
        headers={"Idempotency-Key": "category-create-2"},
    )
    assert child.status_code == 201

    listed = json_client.get(
        "/api/v1/catalog/categories",
        params={"q": "类目", "page": 1, "pageSize": 1, "sort": "name"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert len(listed.json()["items"]) == 1

    updated = json_client.patch(
        f"/api/v1/catalog/categories/{root['id']}",
        json={"name": "新根", "expectedVersion": 1},
        headers={"Idempotency-Key": "category-update-1"},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    update_replay = json_client.patch(
        f"/api/v1/catalog/categories/{root['id']}",
        json={"name": "新根", "expectedVersion": 1},
        headers={"Idempotency-Key": "category-update-1"},
    )
    assert update_replay.status_code == 200
    assert update_replay.json() == updated.json()

    conflict = json_client.patch(
        f"/api/v1/catalog/categories/{root['id']}",
        json={"name": "过期", "expectedVersion": 1},
        headers={"Idempotency-Key": "category-update-2"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"

    status = json_client.post(
        "/api/v1/catalog/categories/status",
        json={"id": root["id"], "status": "inactive", "expectedVersion": 2},
        headers={"Idempotency-Key": "category-status-1"},
    )
    assert status.status_code == 200
    assert status.json()["active"] is False

    status_replay = json_client.post(
        "/api/v1/catalog/categories/status",
        json={"id": root["id"], "status": "inactive", "expectedVersion": 2},
        headers={"Idempotency-Key": "category-status-1"},
    )
    assert status_replay.status_code == 200
    assert status_replay.json() == status.json()


def test_category_rejects_missing_parent_and_cycle(json_client: TestClient) -> None:
    _override(json_client, _principal("item_group:create", "item_group:write"))
    missing = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "孤儿", "parentId": str(uuid4())},
        headers={"Idempotency-Key": "category-missing-parent"},
    )
    assert missing.status_code == 404

    root = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "根"},
        headers={"Idempotency-Key": "category-cycle-root"},
    ).json()
    child = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "子", "parentId": root["id"]},
        headers={"Idempotency-Key": "category-cycle-child"},
    ).json()
    cycle = json_client.patch(
        f"/api/v1/catalog/categories/{root['id']}",
        json={"parentId": child["id"], "expectedVersion": 1},
        headers={"Idempotency-Key": "category-cycle-update"},
    )
    assert cycle.status_code == 409


def test_category_hides_unauthorized_and_missing_resources(json_client: TestClient) -> None:
    _override(json_client, _principal())
    assert json_client.get("/api/v1/catalog/categories").status_code == 404
    missing = str(uuid4())
    assert json_client.patch(f"/api/v1/catalog/categories/{missing}", json={}).status_code == 404
    assert (
        json_client.post(
            "/api/v1/catalog/categories/status",
            json={"id": missing, "status": "inactive"},
            headers={"Idempotency-Key": "category-missing-status"},
        ).status_code
        == 404
    )


def test_category_agent_medium_executes_and_records_context(
    json_client: TestClient,
    api_engine,
) -> None:
    principal = _principal("item_group:create", agent=True)
    _override(json_client, principal)
    response = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "智能体类目"},
        headers={"Idempotency-Key": "category-agent-create"},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["undo"]["entity"] == "Category"
    with Session(api_engine) as session:
        version = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == "Category",
                EntityVersion.entity_id == result["id"],
            )
        )
        audit = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()))
    assert version is not None
    assert version.actor_type == "agent"
    assert version.on_behalf_of == principal.user_id
    assert audit is not None
    assert audit.actor_type == "agent"
    assert audit.actor_user_id == principal.user_id
    assert audit.after_json["agent_id"] == "category-agent"


def test_category_agent_update_and_status_execute_medium_actions(
    json_client: TestClient,
) -> None:
    _override(json_client, _principal("item_group:create", "item_group:write", agent=True))
    created = json_client.post(
        "/api/v1/catalog/categories",
        json={"name": "待改类目"},
        headers={"Idempotency-Key": "category-agent-update-create"},
    ).json()
    updated = json_client.patch(
        f"/api/v1/catalog/categories/{created['id']}",
        json={"name": "已改类目", "expectedVersion": 1},
        headers={"Idempotency-Key": "category-agent-update"},
    )
    assert updated.status_code == 200
    assert updated.json()["undo"]["action"] == "Category.update"
    status = json_client.post(
        "/api/v1/catalog/categories/status",
        json={"id": created["id"], "status": "inactive", "expectedVersion": 2},
        headers={"Idempotency-Key": "category-agent-status"},
    )
    assert status.status_code == 200
    assert status.json()["undo"]["action"] == "Category.status"


@pytest.mark.parametrize(
    "endpoint", ["/api/v1/catalog/categories", "/api/v1/catalog/categories/status"]
)
def test_category_requires_auth(json_client: TestClient, endpoint: str) -> None:
    from crosserp.platform.principal import get_principal

    json_client.app.dependency_overrides.pop(get_principal, None)
    response = (
        json_client.get(endpoint)
        if endpoint.endswith("categories")
        else json_client.post(endpoint, json={})
    )
    assert response.status_code == 401
