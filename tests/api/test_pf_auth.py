"""认证与会话 API 验收测试。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AppUser, PasswordResetToken, SecurityEvent, UserSession


def _create_user(api_engine, username: str = "auth-user", password: str = "password-123") -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username=username, password=password, roles=(Role.ADMIN,))


def _login(client: TestClient, username: str = "auth-user", password: str = "password-123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def test_auth_routes_live_in_dedicated_router(json_client: TestClient) -> None:
    from crosserp.api.routers.auth import router

    paths = {route.path for route in router.routes}
    assert {"/auth/login", "/auth/logout", "/auth/me"} <= paths


def test_login_requires_pydantic_fields(json_client: TestClient) -> None:
    response = json_client.post("/api/v1/auth/login", json={"username": "only-user"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"


def test_five_bad_passwords_lock_account_for_fifteen_minutes(json_client, api_engine) -> None:
    _create_user(api_engine)
    for _ in range(5):
        response = json_client.post(
            "/api/v1/auth/login", json={"username": "auth-user", "password": "wrong"}
        )
        assert response.status_code == 401
    with Session(api_engine) as session:
        user = session.scalar(select(AppUser).where(AppUser.username == "auth-user"))
        assert user is not None
        assert user.failed_logins == 5
        assert user.locked_until is not None
        assert user.locked_until >= datetime.now(UTC) + timedelta(minutes=14)
    response = json_client.post(
        "/api/v1/auth/login", json={"username": "auth-user", "password": "password-123"}
    )
    assert response.status_code == 401


def test_cookie_session_requires_csrf_for_logout(json_client, api_engine) -> None:
    _create_user(api_engine)
    _login(json_client)
    missing = json_client.post("/api/v1/auth/logout")
    wrong = json_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert missing.status_code == wrong.status_code == 403
    assert missing.json()["code"] == wrong.json()["code"] == "CSRF_INVALID"


def test_logout_clears_session_and_calls_revocation_hook(json_client, api_engine) -> None:
    _create_user(api_engine)
    csrf = _login(json_client)
    token = str(json_client.cookies["crosserp_session"])
    response = json_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert json_client.get("/api/v1/auth/me").status_code == 401
    with Session(api_engine) as session:
        row = session.scalar(
            select(UserSession).where(UserSession.id == hashlib.sha256(token.encode()).hexdigest())
        )
        assert row is not None and row.revoked_at is not None
        assert (
            session.scalar(select(SecurityEvent.event).order_by(SecurityEvent.seq.desc()))
            == "logout"
        )


def test_reset_token_is_hashed_single_use_and_records_security_event(
    json_client, api_engine
) -> None:
    _create_user(api_engine)
    response = json_client.post("/api/v1/auth/forgot-password", json={"username": "auth-user"})
    assert response.status_code == 200
    token = response.json()["resetToken"]
    with Session(api_engine) as session:
        row = session.scalar(select(PasswordResetToken))
        assert row is not None
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert token not in row.token_hash
    reset = json_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "new-password-123"}
    )
    assert reset.status_code == 200
    replay = json_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "another-password"}
    )
    assert replay.status_code == 401
    with Session(api_engine) as session:
        events = list(session.scalars(select(SecurityEvent.event).order_by(SecurityEvent.seq)))
        assert "password_reset" in events


def test_expired_session_is_rejected(json_client, api_engine) -> None:
    _create_user(api_engine)
    _login(json_client)
    token = str(json_client.cookies["crosserp_session"])
    with Session(api_engine) as session, session.begin():
        row = session.get(UserSession, hashlib.sha256(token.encode()).hexdigest())
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert json_client.get("/api/v1/auth/me").status_code == 401


def test_idle_session_is_rejected(json_client, api_engine) -> None:
    _create_user(api_engine)
    _login(json_client)
    token = str(json_client.cookies["crosserp_session"])
    with Session(api_engine) as session, session.begin():
        row = session.get(UserSession, hashlib.sha256(token.encode()).hexdigest())
        assert row is not None
        row.last_seen_at = datetime.now(UTC) - timedelta(hours=2, seconds=1)
    assert json_client.get("/api/v1/auth/me").status_code == 401


def test_disabled_user_cannot_login_and_existing_session_is_invalid(
    json_client, api_engine
) -> None:
    _create_user(api_engine)
    _login(json_client)
    with Session(api_engine) as session, session.begin():
        user = session.scalar(select(AppUser).where(AppUser.username == "auth-user"))
        assert user is not None
        user.is_active = False
    assert json_client.get("/api/v1/auth/me").status_code == 401
    json_client.cookies.clear()
    response = json_client.post(
        "/api/v1/auth/login", json={"username": "auth-user", "password": "password-123"}
    )
    assert response.status_code == 401


def test_me_returns_permission_scope_policy_ai_currency_and_timezone(
    json_client, api_engine
) -> None:
    _create_user(api_engine)
    _login(json_client)
    body = json_client.get("/api/v1/auth/me").json()
    assert body["permissions"]
    assert "dataScopes" in body and "fieldPolicies" in body
    assert body["aiMode"] == "normal"
    assert body["baseCurrency"] == "CNY"
    assert body["timezone"] == "Asia/Shanghai"
