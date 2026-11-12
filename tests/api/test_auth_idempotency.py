"""未登录公开写接口不参与幂等回放。依据 08 第 4.8 节和前端自动带 Idempotency-Key。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import IdempotencyKey, PasswordResetToken


def _user(engine, username: str, password: str) -> None:
    with Session(engine) as session, session.begin():
        create_user(session, username=username, password=password, roles=(Role.OPERATOR,))


def test_login_with_idempotency_key_executes_again(json_client: TestClient, api_engine) -> None:
    _user(api_engine, "login-a", "Login-test-password-123")
    headers = {"Idempotency-Key": "login-key"}
    body = {"username": "login-a", "password": "Login-test-password-123"}

    first = json_client.post("/api/v1/auth/login", json=body, headers=headers)
    assert first.status_code == 200
    first_cookie = json_client.cookies["crosserp_session"]
    json_client.cookies.clear()

    second = json_client.post("/api/v1/auth/login", json=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["userId"] == first.json()["userId"]
    assert json_client.cookies["crosserp_session"] != first_cookie
    me = json_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["userId"] == first.json()["userId"]
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


def test_same_login_key_issues_the_callers_own_session(json_client: TestClient, api_engine) -> None:
    _user(api_engine, "login-a", "Login-test-password-123")
    _user(api_engine, "login-b", "Login-test-password-456")
    headers = {"Idempotency-Key": "shared-login-key"}

    first = json_client.post(
        "/api/v1/auth/login",
        json={"username": "login-a", "password": "Login-test-password-123"},
        headers=headers,
    )
    assert first.status_code == 200
    json_client.cookies.clear()

    second = json_client.post(
        "/api/v1/auth/login",
        json={"username": "login-b", "password": "Login-test-password-456"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["userId"] != first.json()["userId"]
    me = json_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["userId"] == second.json()["userId"]


def test_forgot_and_reset_with_key_are_not_replayed(json_client: TestClient, api_engine) -> None:
    _user(api_engine, "reset-user", "Reset-test-password-123")
    headers = {"Idempotency-Key": "reset-key"}

    first = json_client.post(
        "/api/v1/auth/forgot-password", json={"username": "reset-user"}, headers=headers
    )
    second = json_client.post(
        "/api/v1/auth/forgot-password", json={"username": "reset-user"}, headers=headers
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "accepted"
    assert first.json()["resetToken"] != second.json()["resetToken"]

    reset = json_client.post(
        "/api/v1/auth/reset-password",
        json={"token": first.json()["resetToken"], "newPassword": "Reset-test-password-456"},
        headers=headers,
    )
    assert reset.status_code == 200
    again = json_client.post(
        "/api/v1/auth/reset-password",
        json={"token": first.json()["resetToken"], "newPassword": "Reset-test-password-789"},
        headers=headers,
    )
    assert again.status_code == 401
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0
        assert session.scalar(select(func.count()).select_from(PasswordResetToken)) == 2
