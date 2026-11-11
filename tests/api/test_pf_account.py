"""我的账户接口验收。"""

from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.security import SecurityEvent
from crosserp.auth.roles import Role
from crosserp.auth.sessions import create_session
from crosserp.db.repo.users import create_user
from crosserp.db.schema import ApiToken, AuditLog, UserSession
from crosserp.platform.principal import ActorType, Principal


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def test_account_routes_live_in_account_router() -> None:
    from crosserp.api.routers import account

    paths = {route.path for route in account.router.routes}
    assert {
        "/account/profile",
        "/account/password",
        "/account/tokens",
        "/account/tokens/{id}/revoke",
        "/account/sessions",
        "/account/sessions/{id}",
    } <= paths


def test_profile_patch_forbids_identity_fields(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username="profile-user", password="password-123", roles=(Role.ADMIN,))
    csrf = _login(json_client, "profile-user", "password-123")

    response = json_client.patch(
        "/api/v1/account/profile",
        json={"displayName": "新名字", "username": "attacker", "roles": ["admin"]},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_password_change_revokes_other_sessions(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="password-user", password="password-123", roles=(Role.ADMIN,)
        )
        user_id = user.id
        other = create_session(
            session,
            user,
            ip="127.0.0.2",
            user_agent="other",
            hours=12,
        )
    csrf = _login(json_client, "password-user", "password-123")

    response = json_client.post(
        "/api/v1/account/password",
        json={"currentPassword": "password-123", "newPassword": "new-password-123"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    with Session(api_engine) as session:
        rows = list(session.scalars(select(UserSession).where(UserSession.user_id == user_id)))
        assert any(
            row.id == hashlib.sha256(other.value.encode()).hexdigest() and row.revoked_at
            for row in rows
        )
        assert session.scalar(
            select(SecurityEvent).where(SecurityEvent.event == "password_changed")
        )


def test_session_scope_and_kick_are_limited_to_current_user(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username="session-owner", password="password-123", roles=(Role.ADMIN,))
        other = create_user(
            session, username="session-other", password="password-123", roles=(Role.ADMIN,)
        )
        foreign = create_session(session, other, ip=None, user_agent=None, hours=12)
    csrf = _login(json_client, "session-owner", "password-123")

    listed = json_client.get("/api/v1/account/sessions")
    assert listed.status_code == 200
    assert all(item["id"] != foreign.value[:16] for item in listed.json()["items"])

    kicked = json_client.delete(
        f"/api/v1/account/sessions/{foreign.value[:16]}",
        headers={"X-CSRF-Token": csrf},
    )
    assert kicked.status_code == 404


def test_revoked_token_is_rejected_immediately(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(
            session, username="token-revoke-user", password="password-123", roles=(Role.ADMIN,)
        )
    csrf = _login(json_client, "token-revoke-user", "password-123")
    created = json_client.post(
        "/api/v1/account/tokens",
        json={"name": "one-time"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200
    token = created.json()["token"]
    token_id = created.json()["id"]
    with Session(api_engine) as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "ApiToken.create"))
        assert audit is not None
        assert token not in str(audit.after_json)

    revoked = json_client.post(
        f"/api/v1/account/tokens/{token_id}/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoked.status_code == 200

    json_client.cookies.clear()
    rejected = json_client.get(
        "/api/v1/account/tokens", headers={"Authorization": f"Bearer {token}"}
    )
    assert rejected.status_code == 401
    with Session(api_engine) as session:
        row = session.get(ApiToken, UUID(token_id))
        assert row is not None
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()


def test_account_writes_have_audit_and_security_event(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(
            session, username="audit-account-user", password="password-123", roles=(Role.ADMIN,)
        )
    csrf = _login(json_client, "audit-account-user", "password-123")

    response = json_client.patch(
        "/api/v1/account/profile",
        json={"displayName": "已审计"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    with Session(api_engine) as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "UserAccount.update"))
        assert session.scalar(select(SecurityEvent).where(SecurityEvent.event == "profile_updated"))


def test_agent_is_rejected_from_critical_account_write(
    json_client: TestClient, api_engine, monkeypatch
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="agent-account-user", password="password-123", roles=(Role.ADMIN,)
        )
        user_id = user.id
    _login(json_client, "agent-account-user", "password-123")
    monkeypatch.setattr(
        "crosserp.api.routers._platform_common.get_principal",
        lambda _request: Principal(
            user_id=user_id,
            roles=frozenset({"admin"}),
            actor_type=ActorType.AGENT,
            agent_id="agent-1",
            on_behalf_of=user_id,
        ),
    )

    response = json_client.patch(
        "/api/v1/account/profile",
        json={"displayName": "不应成功"},
        headers={"X-CSRF-Token": str(json_client.cookies["crosserp_csrf"])},
    )

    assert response.status_code == 403
