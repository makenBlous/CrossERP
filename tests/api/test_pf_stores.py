"""店铺与数据范围 API 验收。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AppSetting, AuditLog, Store
from crosserp.platform.principal import ActorType, Principal


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _create_admin(api_engine, username: str = "store-admin") -> UUID:
    with Session(api_engine) as session, session.begin():
        return create_user(
            session,
            username=username,
            password="Store-test-password-123",
            roles=(Role.ADMIN,),
        ).id


def test_store_list_uses_store_data_scope(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="store-scope",
            password="Store-test-password-123",
            roles=(Role.OPERATOR,),
        )
        visible = Store(platform="amazon", marketplace="US", name="visible", currency="USD")
        hidden = Store(platform="amazon", marketplace="DE", name="hidden", currency="EUR")
        session.add_all([visible, hidden])
        session.flush()
        session.add(
            AppSetting(
                key=f"data_scope:{user.id}",
                value_json={"storeIds": [str(visible.id)]},
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
    _login(json_client, "store-scope", "Store-test-password-123")

    response = json_client.get("/api/v1/stores")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["visible"]


def test_store_create_is_idempotent_and_conflicting_body_is_rejected(
    json_client: TestClient, api_engine
) -> None:
    _create_admin(api_engine)
    csrf = _login(json_client, "store-admin", "Store-test-password-123")
    headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "store-create-1"}
    payload = {
        "platform": "amazon",
        "marketplace": "US",
        "name": "US Store",
        "currency": "USD",
        "legalEntity": "CrossERP Ltd",
    }

    first = json_client.post("/api/v1/admin/stores", json=payload, headers=headers)
    replay = json_client.post("/api/v1/admin/stores", json=payload, headers=headers)
    conflict = json_client.post(
        "/api/v1/admin/stores",
        json={**payload, "name": "Different"},
        headers=headers,
    )

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    with Session(api_engine) as session:
        assert session.scalar(select(Store).where(Store.name == "US Store")) is not None
        assert session.scalar(select(Store).where(Store.name == "Different")) is None


def test_store_update_requires_expected_version(json_client: TestClient, api_engine) -> None:
    _create_admin(api_engine, "store-version")
    with Session(api_engine) as session, session.begin():
        row = Store(platform="amazon", marketplace="US", name="versioned", currency="USD")
        session.add(row)
        session.flush()
        store_id = row.id
    csrf = _login(json_client, "store-version", "Store-test-password-123")
    headers = {"X-CSRF-Token": csrf}

    updated = json_client.patch(
        f"/api/v1/admin/stores/{store_id}",
        json={"name": "updated", "expectedVersion": 1},
        headers=headers,
    )
    conflict = json_client.patch(
        f"/api/v1/admin/stores/{store_id}",
        json={"name": "stale", "expectedVersion": 1},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"


def test_store_writes_require_human_principal(
    json_client: TestClient, api_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = _create_admin(api_engine, "store-agent")
    csrf = _login(json_client, "store-agent", "Store-test-password-123")
    monkeypatch.setattr(
        "crosserp.api.routers.platform.get_principal",
        lambda _request: Principal(
            user_id=user_id,
            roles=frozenset({Role.ADMIN.value}),
            actor_type=ActorType.AGENT,
            agent_id="store-agent",
            on_behalf_of=user_id,
        ),
    )

    response = json_client.post(
        "/api/v1/admin/stores",
        json={
            "platform": "amazon",
            "marketplace": "US",
            "name": "agent-store",
            "currency": "USD",
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AI_AUTONOMY_CAPPED"


def test_data_scope_delegates_to_permission_service(
    json_client: TestClient, api_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_admin(api_engine, "scope-service")
    _login(json_client, "scope-service", "Store-test-password-123")
    sentinel = {"storeIds": ["permission-service-store"]}
    monkeypatch.setattr(
        "crosserp.api.routers.stores._permission_service.data_scope_filter",
        lambda _principal, _entity: sentinel,
    )

    response = json_client.get("/api/v1/me/data-scope")

    assert response.status_code == 200
    assert response.json() == {"scopes": [sentinel]}


def test_store_write_is_audited(json_client: TestClient, api_engine) -> None:
    _create_admin(api_engine, "store-audit")
    csrf = _login(json_client, "store-audit", "Store-test-password-123")

    response = json_client.post(
        "/api/v1/admin/stores",
        json={
            "platform": "shopify",
            "marketplace": "US",
            "name": "audited-store",
            "currency": "USD",
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 201
    with Session(api_engine) as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "Store.create").order_by(AuditLog.seq.desc())
        )
        assert audit is not None
        assert audit.target_type == "Store"
