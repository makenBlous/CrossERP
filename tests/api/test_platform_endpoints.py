"""P0 平台接口验收：认证、幂等、Token、数据范围和会话钩子。"""  # noqa: RUF002

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AppSetting, Delegation, Store


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def test_platform_requires_login_with_uniform_error(json_client: TestClient) -> None:
    response = json_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert set(response.json()) == {"code", "message", "details", "requestId"}


def test_token_plaintext_is_returned_once(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username="token-user", password="password-123", roles=(Role.ADMIN,))
    csrf = _login(json_client, "token-user", "password-123")
    first = json_client.post(
        "/api/v1/account/tokens", json={"name": "test"}, headers={"X-CSRF-Token": csrf}
    )
    assert first.status_code == 200
    assert first.json()["token"].startswith("cerp_")
    listed = json_client.get("/api/v1/account/tokens")
    assert listed.status_code == 200
    assert "token" not in listed.json()["items"][0]


def test_store_idempotency_and_data_scope(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="scope-user", password="password-123", roles=(Role.OPERATOR,)
        )
        first = Store(platform="amazon", marketplace="US", name="visible", currency="USD")
        second = Store(platform="amazon", marketplace="DE", name="hidden", currency="EUR")
        session.add_all([first, second])
        session.flush()
        user_role = session.get(AppSetting, f"data_scope:{user.id}")
        if user_role is None:
            session.add(
                AppSetting(
                    key=f"data_scope:{user.id}",
                    value_json={"storeIds": [str(first.id)]},
                    updated_by=user.id,
                    updated_at=datetime.now(UTC),
                )
            )
    _login(json_client, "scope-user", "password-123")
    first_response = json_client.get("/api/v1/stores")
    replay = json_client.get("/api/v1/stores")
    conflict = json_client.get("/api/v1/stores")
    assert first_response.status_code == replay.status_code == conflict.status_code == 200
    assert [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]] == [
        "visible"
    ]


def test_logout_revokes_delegation_hook(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="logout-user", password="password-123", roles=(Role.ADMIN,)
        )
        user_id = user.id
    csrf = _login(json_client, "logout-user", "password-123")
    token = json_client.cookies["crosserp_session"]
    with Session(api_engine) as session, session.begin():
        session.add(
            Delegation(
                id=uuid4(),
                user_id=user_id,
                session_id=hashlib.sha256(token.encode()).hexdigest(),
                scopes=[],
                status="active",
                expires_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
        )
    response = json_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    with Session(api_engine) as session:
        assert session.scalar(select(Delegation.status)) == "revoked"
