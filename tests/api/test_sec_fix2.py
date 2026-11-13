from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import DocumentLink, IamDataScopeRule, Store, UserRole
from crosserp.iam.catalog import load_role_templates
from crosserp.iam.service import IAMService
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.principal import Principal


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return str(client.cookies["crosserp_csrf"])


def _link(from_type: str, from_id: str, to_type: str, to_id: str) -> DocumentLink:
    return DocumentLink(
        id=uuid4(),
        from_type=from_type,
        from_id=from_id,
        to_type=to_type,
        to_id=to_id,
        relation="creates",
        created_at=datetime.now(UTC),
    )


def test_documents_use_iam_entity_scope_even_when_user_scope_is_broad(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="sec-doc-scope", password="password-123", roles=(Role.OPERATOR,)
        )
        visible = Store(
            id=uuid4(), platform="amazon", marketplace="US", name="visible", currency="USD"
        )
        hidden = Store(
            id=uuid4(), platform="amazon", marketplace="DE", name="hidden", currency="EUR"
        )
        visible_id = str(visible.id)
        session.add_all([visible, hidden])
        session.add_all(
            [
                _link("Store", str(visible.id), "Order", "visible-order"),
                _link("Store", str(hidden.id), "Order", "hidden-order"),
            ]
        )
        session.add(
            IamDataScopeRule(
                name="document-only-scope",
                entity="DocumentLink",
                scope_type="storeIds",
                values=[str(visible.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
    _login(json_client, "sec-doc-scope", "password-123")

    response = json_client.get("/api/v1/documents/links")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["from"]["id"] == visible_id


def test_me_uses_current_iam_permissions_after_revoke(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="sec-me-revoke", password="password-123", roles=(Role.OPERATOR,)
        )
        user_id = user.id
    _login(json_client, "sec-me-revoke", "password-123")
    IAMService(api_engine).set_override(user_id, "user:read", effect="deny", reason="sec-fix2-test")

    response = json_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert "user:read" not in response.json()["permissions"]


def test_dispatcher_factory_requires_undo_restore_registry() -> None:
    class PermissionService:
        def require(self, *_args, **_kwargs) -> None:
            return None

        def data_scope_filter(self, *_args, **_kwargs) -> dict[str, object]:
            return {}

        def current_permissions(self, principal: Principal) -> frozenset[str]:
            return principal.permissions

    session = Session()
    with pytest.raises(TypeError, match="undo_restore"):
        make_action_dispatcher(session, PermissionService())
    session.close()


def test_data_scope_denial_is_forbidden() -> None:
    assert APIError(ErrorCode.DATA_SCOPE_DENIED, "范围不足").status_code == 403


def test_all_seeded_roles_have_self_service_permissions(api_engine) -> None:
    service = IAMService(api_engine)
    role_ids = [*load_role_templates(), "admin", "operator", "finance", "viewer", "auditor"]
    for role_id in role_ids:
        user_id = uuid4()
        with Session(api_engine) as session, session.begin():
            user = create_user(
                session,
                username=f"sec-role-{user_id.hex[:12]}",
                password="password-123",
            )
            session.add(UserRole(user_id=user.id, role=role_id, granted_at=datetime.now(UTC)))
            user_id = user.id
        principal = Principal(user_id=user_id, roles=frozenset({role_id}))
        assert "user:read" in service.current_permissions(principal)
        assert "user:write" in service.current_permissions(principal)


def test_every_seeded_role_can_change_own_password_but_not_admin_users(
    json_client: TestClient, api_engine
) -> None:
    role_ids = [*load_role_templates(), "admin", "operator", "finance", "viewer", "auditor"]
    for role_id in role_ids:
        username = f"sec-password-{uuid4().hex[:12]}"
        with Session(api_engine) as session, session.begin():
            user = create_user(session, username=username, password="password-123")
            session.add(UserRole(user_id=user.id, role=role_id, granted_at=datetime.now(UTC)))
        csrf = _login(json_client, username, "password-123")
        changed = json_client.post(
            "/api/v1/account/password",
            json={"currentPassword": "password-123", "newPassword": "password-456"},
            headers={"X-CSRF-Token": csrf},
        )
        assert changed.status_code == 200, (role_id, changed.text)
        denied = json_client.post(
            "/api/v1/admin/users",
            json={"username": f"blocked-{uuid4().hex[:8]}", "password": "password-789"},
        )
        expected = 201 if role_id in {"owner_manager", "admin"} else 404
        assert denied.status_code == expected, (role_id, denied.text)
        json_client.cookies.clear()
