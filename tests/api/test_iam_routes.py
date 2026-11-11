from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from crosserp.api.routers.iam import _ROUTES
from crosserp.db.repo.users import create_user
from crosserp.platform.principal import Principal, get_principal


def test_every_iam_route_has_success_and_denial(json_client, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username=f"route-{uuid4().hex[:8]}", password="Api-test-password-123"
        )
        target = str(user.id)
    role_id = "admin"
    custom_role = None
    grant_id = None
    review_id = None
    user_id = uuid4()
    admin = Principal(user_id=user_id, roles=frozenset({"admin"}))
    viewer = Principal(user_id=user_id, roles=frozenset({"viewer"}))
    json_client.app.dependency_overrides[get_principal] = lambda: admin
    try:
        for method, template, _entity, _action, _permission, _risk, _status in _ROUTES:
            path = template.replace("{id}", target).replace("{key}", "route-setting")
            if "/admin/roles/" in path:
                path = path.replace(target, custom_role or role_id)
            if "/temp-grants/" in path:
                if grant_id is None:
                    create = json_client.post(
                        "/api/v1/admin/temp-grants",
                        json={"userId": target, "permission": "report:read"},
                    )
                    assert create.status_code == 201, create.text
                    grant_id = create.json()["data"]["id"]
                path = path.replace(target, grant_id)
            if "/access-reviews/" in path:
                if review_id is None:
                    create = json_client.post(
                        "/api/v1/admin/access-reviews", json={"userId": target}
                    )
                    assert create.status_code == 201, create.text
                    review_id = create.json()["data"]["id"]
                path = path.replace(target, review_id)
            payload = {
                "displayName": "Updated",
                "active": True,
                "enabled": True,
                "roles": ["viewer"],
                "values": ["all"],
                "userId": target,
                "permission": "report:read",
                "name": "route",
                "fieldKey": "salary",
                "scopeType": "store",
                "username": f"route-created-{uuid4().hex[:8]}",
                "password": "Api-test-password-456",
            }
            if _action == "Role.set_permissions":
                payload["permissions"] = {"report:read": "allow", "permission:write": "allow"}
            if _action == "PermissionPoint.update":
                payload["cells"] = [
                    {"roleId": role_id, "permissionKey": "report:read", "effect": "allow"}
                ]
            response = json_client.request(method, "/api/v1" + path, json=payload)
            assert response.status_code in {200, 201}, (
                method,
                path,
                response.status_code,
                response.text,
            )
            if _action == "Role.create":
                custom_role = response.json()["data"]["id"]
            json_client.app.dependency_overrides[get_principal] = lambda: viewer
            denied = json_client.request(method, "/api/v1" + path, json=payload)
            assert denied.status_code == 404, (method, path, denied.status_code, denied.text)
            json_client.app.dependency_overrides[get_principal] = lambda: admin
    finally:
        json_client.app.dependency_overrides.pop(get_principal, None)
