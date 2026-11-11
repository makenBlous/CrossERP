# mypy: ignore-errors
# ruff: noqa

"""系统与权限 JSON API。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import hash_password
from crosserp.db.schema import AppUser, UserRole
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.iam.catalog import load_catalog
from crosserp.iam.service import IAMService
from crosserp.platform.dispatcher import ActionDispatcher
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["系统与权限"])


def _session(request: Request) -> Session:
    return Session(request.app.state.database_engine)


def _service(request: Request) -> tuple[IAMService, DefaultPermissionService]:
    return request.app.state.iam_service, request.app.state.permission_service


def _principal_check(request: Request, principal: Principal, permission: str, risk: str) -> None:
    permission_service = _service(request)[1]

    def check_permission(**_: Any) -> None:
        permission_service.iam.require(principal, permission, risk_tier=risk)

    try:
        ActionDispatcher().dispatch(
            principal=principal,
            permission=permission,
            risk_tier=risk,
            action=permission,
            business_action=lambda: None,
            hooks={"permission": check_permission},
        )
    except PermissionError as exc:
        raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "智能体不能执行危风险动作") from exc
    except APIError:
        raise


def _result(data: Any, *, created: bool = False) -> dict[str, Any]:
    return {"data": data, "status": "created" if created else "ok"}


def _audit(request: Request, principal: Principal, entity: str, action: str, diff: Any) -> None:
    with _session(request) as session, session.begin():
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity=entity,
            action=action,
            diff=diff,
            request_id=getattr(request.state, "request_id", None),
        )
        if entity in {
            "Role",
            "PermissionPoint",
            "FieldPolicy",
            "DataScopeRule",
            "TempGrant",
            "AccessReview",
            "SodRule",
            "ModuleSwitch",
            "Dictionary",
            "SystemSetting",
        } or action in {"User.set_roles", "User.set_overrides"}:
            record_security(
                session,
                SecurityEventName.PERMISSION_CHANGED,
                user_id=principal.user_id,
                target_user_id=principal.effective_user_id,
                request_id=getattr(request.state, "request_id", None),
                detail={"entity": entity, "action": action, "diff": diff},
            )


def _record(obj: Any) -> dict[str, Any]:
    if isinstance(obj, AppUser):
        return {
            "id": str(obj.id),
            "username": obj.username,
            "displayName": obj.display_name,
            "isActive": obj.is_active,
            "permissionVersion": obj.permission_version,
        }
    if isinstance(obj, dict):
        return obj
    return {"id": str(obj)}


def _generic(
    request: Request,
    principal: Principal,
    permission: str,
    risk: str,
    *,
    path_id: str | None,
    path_key: str | None,
    payload: dict[str, Any],
    entity: str,
    action: str,
    method: str,
) -> Any:
    _principal_check(request, principal, permission, risk)
    iam, _ = _service(request)
    if entity == "PermissionPoint":
        if method == "GET":
            return {
                "items": load_catalog(),
                "page": 1,
                "pageSize": len(load_catalog()),
                "total": len(load_catalog()),
            }
        return _result(payload)
    if entity == "User":
        with _session(request) as session:
            if method == "GET" and path_id is None:
                rows = list(session.scalars(select(AppUser).order_by(AppUser.username)))
                return {
                    "items": [_record(row) for row in rows],
                    "page": 1,
                    "pageSize": len(rows),
                    "total": len(rows),
                }
            user = _get_user(session, path_id) if path_id else None
            if method == "GET":
                return _record(user)
            if method == "POST" and path_id is None:
                username = str(payload.get("username", "user-" + uuid4().hex[:8]))
                password = str(payload.get("password", "CrossERP-demo-password"))
                user = AppUser(
                    id=uuid4(),
                    username=username,
                    display_name=str(payload.get("displayName", username)),
                    password_hash=hash_password(password),
                    is_active=True,
                    failed_logins=0,
                    password_changed_at=datetime.now(UTC),
                    must_change_password=True,
                    created_at=datetime.now(UTC),
                    permission_version=0,
                )
                session.add(user)
                session.commit()
                _audit(request, principal, entity, action, _record(user))
                return _result(_record(user), created=True)
            if user is None:
                raise not_found()
            if method == "PATCH":
                if "displayName" in payload:
                    user.display_name = str(payload["displayName"])
                if "isActive" in payload:
                    user.is_active = bool(payload["isActive"])
                user.permission_version += 1
                session.commit()
                _audit(request, principal, entity, action, payload)
                return _result(_record(user))
            if action == "User.set_roles":
                roles = {str(item) for item in payload.get("roles", [])}
                for row in list(
                    session.scalars(select(UserRole).where(UserRole.user_id == user.id))
                ):
                    session.delete(row)
                for role in roles:
                    session.add(UserRole(user_id=user.id, role=role, granted_at=datetime.now(UTC)))
                user.permission_version += 1
                session.commit()
                _audit(request, principal, entity, action, payload)
                iam.user_roles[user.id] = roles
                iam._bump(user.id)
                return _result({"id": str(user.id), "roles": sorted(roles)})
            if action == "User.set_overrides":
                iam.overrides[user.id] = []
                for item in payload.get("overrides", []):
                    if isinstance(item, dict) and item.get("permission"):
                        iam.set_override(
                            user.id,
                            str(item["permission"]),
                            effect="deny" if item.get("effect") == "deny" else "allow",
                            reason=str(item.get("reason", "user override")),
                        )
                user.permission_version += 1
                session.commit()
                _audit(request, principal, entity, action, payload)
                return _result({"id": str(user.id), "overrides": payload.get("overrides", [])})
            if action == "User.reset_password":
                user.password_hash = hash_password(
                    str(payload.get("password", "CrossERP-reset-password"))
                )
                user.password_changed_at = datetime.now(UTC)
                user.must_change_password = True
                session.commit()
                _audit(request, principal, entity, action, {"passwordReset": True})
                return _result(_record(user))
            if action == "User.read_effective_permissions":
                iam.user_roles[user.id] = {
                    row.role
                    for row in session.scalars(select(UserRole).where(UserRole.user_id == user.id))
                }
                effective = [
                    iam.effective_permission(user.id, str(point["key"])) for point in load_catalog()
                ]
                return {
                    "items": [
                        {
                            "permission": x.permission,
                            "allowed": x.allowed,
                            "sources": list(x.sources),
                            "deniedBy": list(x.denied_by),
                            "dataScopes": list(x.data_scopes),
                        }
                        for x in effective
                    ],
                    "total": len(effective),
                }
    if entity == "Role":
        if method == "GET" and path_id is None:
            rows = list(iam.roles.values())
            return {
                "items": [
                    {
                        "id": r.id,
                        "name": r.name or r.id,
                        "parentIds": sorted(r.parent_ids),
                        "permissions": r.permissions,
                        "active": r.active,
                    }
                    for r in rows
                ],
                "total": len(rows),
            }
        if method == "POST" and path_id is None:
            slug = str(payload.get("slug", payload.get("name", "role-" + uuid4().hex[:8])))
            role = iam.create_role(
                slug,
                name=str(payload.get("name", slug)),
                permissions=set(payload.get("permissions", [])),
                parent_ids=set(payload.get("parentIds", [])),
                data_scopes=set(payload.get("dataScopes", [])),
            )
            result = _result({"id": role.id, "name": role.name}, created=True)
            _audit(request, principal, entity, action, result)
            return result
    if entity == "TempGrant":
        if method == "POST" and path_id is None:
            try:
                user_id = UUID(str(payload["userId"]))
            except (KeyError, ValueError) as exc:
                raise APIError(ErrorCode.VALIDATION_FAILED, "userId 无效") from exc
            raw_expires = payload.get("expiresAt")
            try:
                expires_at = (
                    datetime.fromisoformat(str(raw_expires))
                    if raw_expires
                    else datetime.now(UTC) + timedelta(hours=1)
                )
            except ValueError as exc:
                raise APIError(ErrorCode.VALIDATION_FAILED, "expiresAt 无效") from exc
            grant = iam.set_temporary_grant(
                user_id,
                str(payload["permission"]),
                effect="deny" if payload.get("effect") == "deny" else "allow",
                reason=str(payload.get("reason", "temporary grant")),
                expires_at=expires_at,
            )
            result = _result(
                {"id": str(uuid4()), "userId": str(user_id), "permission": grant.permission},
                created=True,
            )
            _audit(request, principal, entity, action, result)
            return result
        if method == "POST" and path_id:
            for grants in iam.temporary_grants.values():
                for grant in grants:
                    if (
                        str(grant.user_id) == str(payload.get("userId", ""))
                        or path_id == grant.permission
                    ):
                        grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            result = _result({"id": path_id, "revoked": True})
            _audit(request, principal, entity, action, result)
            return result
        role = iam.roles.get(path_id or "")
        if role is None:
            raise not_found()
        if action == "Role.copy":
            slug = str(payload.get("slug", role.id + "-copy"))
            copy = iam.create_role(
                slug,
                name=str(payload.get("name", slug)),
                permissions=set(role.permissions),
                parent_ids=set(role.parent_ids),
                data_scopes=set(role.data_scopes),
            )
            result = _result({"id": copy.id, "name": copy.name}, created=True)
            _audit(request, principal, entity, action, result)
            return result
        if action == "Role.update":
            iam.update_role(
                path_id or "",
                parent_ids=set(payload["parentIds"]) if "parentIds" in payload else None,
                active=bool(payload["active"]) if "active" in payload else None,
            )
        if action == "Role.set_permissions":
            iam.update_role(
                path_id or "",
                permissions={str(k): str(v) for k, v in payload.get("permissions", {}).items()},
            )
            result = _result(
                {
                    "id": role.id,
                    "name": role.name or role.id,
                    "permissions": role.permissions,
                    "parentIds": sorted(role.parent_ids),
                    "active": role.active,
                }
            )
            _audit(request, principal, entity, action, result)
            return result
    if method == "GET":
        return {"items": [], "page": 1, "pageSize": 0, "total": 0}
    result = _result(
        {"id": path_id or path_key or str(uuid4()), **payload}, created=method == "POST"
    )
    if method != "GET":
        _audit(request, principal, entity, action, result)
    return result


def _get_user(session: Session, value: str | None) -> AppUser:
    try:
        user = session.get(AppUser, UUID(value or ""))
    except ValueError:
        user = None
    if user is None:
        raise not_found()
    return user


_ROUTES = [
    ("GET", "/admin/users", "User", "User.list", "user_admin:read", "none", 200),
    ("POST", "/admin/users", "User", "User.create", "user_admin:create", "critical", 201),
    ("GET", "/admin/users/{id}", "User", "User.get", "user_admin:read", "none", 200),
    ("PATCH", "/admin/users/{id}", "User", "User.update", "user_admin:write", "critical", 200),
    (
        "PUT",
        "/admin/users/{id}/roles",
        "User",
        "User.set_roles",
        "permission:write",
        "critical",
        200,
    ),
    (
        "PUT",
        "/admin/users/{id}/overrides",
        "User",
        "User.set_overrides",
        "permission:write",
        "critical",
        200,
    ),
    (
        "POST",
        "/admin/users/{id}/reset-password",
        "User",
        "User.reset_password",
        "user_admin:write",
        "critical",
        200,
    ),
    (
        "GET",
        "/admin/users/{id}/effective-permissions",
        "User",
        "User.read_effective_permissions",
        "permission:read",
        "none",
        200,
    ),
    ("GET", "/admin/roles", "Role", "Role.list", "permission:read", "none", 200),
    ("POST", "/admin/roles", "Role", "Role.create", "permission:write", "critical", 201),
    ("GET", "/admin/roles/{id}", "Role", "Role.get", "permission:read", "none", 200),
    ("PATCH", "/admin/roles/{id}", "Role", "Role.update", "permission:write", "critical", 200),
    (
        "PUT",
        "/admin/roles/{id}/permissions",
        "Role",
        "Role.set_permissions",
        "permission:write",
        "critical",
        200,
    ),
    ("POST", "/admin/roles/{id}/copy", "Role", "Role.copy", "permission:write", "critical", 200),
    (
        "GET",
        "/admin/permissions",
        "PermissionPoint",
        "PermissionPoint.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "GET",
        "/admin/permission-matrix",
        "PermissionPoint",
        "PermissionPoint.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "PUT",
        "/admin/permission-matrix",
        "PermissionPoint",
        "PermissionPoint.update",
        "permission:write",
        "critical",
        200,
    ),
    (
        "GET",
        "/admin/field-policies",
        "FieldPolicy",
        "FieldPolicy.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "PUT",
        "/admin/field-policies/{id}",
        "FieldPolicy",
        "FieldPolicy.update",
        "permission:write",
        "critical",
        200,
    ),
    (
        "GET",
        "/admin/data-scopes",
        "DataScopeRule",
        "DataScopeRule.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "PUT",
        "/admin/data-scopes/{id}",
        "DataScopeRule",
        "DataScopeRule.update",
        "permission:write",
        "critical",
        200,
    ),
    ("GET", "/admin/temp-grants", "TempGrant", "TempGrant.list", "permission:read", "none", 200),
    (
        "POST",
        "/admin/temp-grants",
        "TempGrant",
        "TempGrant.create",
        "permission:write",
        "critical",
        201,
    ),
    (
        "POST",
        "/admin/temp-grants/{id}/revoke",
        "TempGrant",
        "TempGrant.revoke",
        "permission:write",
        "critical",
        200,
    ),
    (
        "GET",
        "/admin/access-reviews",
        "AccessReview",
        "AccessReview.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "POST",
        "/admin/access-reviews",
        "AccessReview",
        "AccessReview.create",
        "permission:approve",
        "critical",
        201,
    ),
    (
        "POST",
        "/admin/access-reviews/{id}/confirm",
        "AccessReview",
        "AccessReview.confirm",
        "permission:approve",
        "critical",
        200,
    ),
    ("GET", "/admin/sod-rules", "SodRule", "SodRule.list", "permission:read", "none", 200),
    (
        "PUT",
        "/admin/sod-rules/{id}",
        "SodRule",
        "SodRule.update",
        "permission:write",
        "critical",
        200,
    ),
    ("GET", "/admin/modules", "ModuleSwitch", "ModuleSwitch.list", "permission:read", "none", 200),
    (
        "PATCH",
        "/admin/modules/{id}",
        "ModuleSwitch",
        "ModuleSwitch.update",
        "system:write",
        "critical",
        200,
    ),
    ("GET", "/admin/dictionaries", "Dictionary", "Dictionary.list", "permission:read", "none", 200),
    (
        "PUT",
        "/admin/dictionaries/{key}",
        "Dictionary",
        "Dictionary.update",
        "system:write",
        "critical",
        200,
    ),
    (
        "GET",
        "/admin/settings",
        "SystemSetting",
        "SystemSetting.list",
        "permission:read",
        "none",
        200,
    ),
    (
        "PUT",
        "/admin/settings",
        "SystemSetting",
        "SystemSetting.update",
        "system:write",
        "critical",
        200,
    ),
]


def _make_endpoint(entity: str, action: str, permission: str, risk: str, method: str, status: int):
    def endpoint(
        request: Request,
        id: str | None = None,
        key: str | None = None,
        payload: dict[str, Any] = Body(default={}),
        principal: Principal = Depends(get_principal),
    ) -> Any:
        return _generic(
            request,
            principal,
            permission,
            risk,
            path_id=id,
            path_key=key,
            payload=payload,
            entity=entity,
            action=action,
            method=method,
        )

    endpoint.__name__ = f"{method.lower()}_{entity}_{action.replace('.', '_')}"
    return api_endpoint(entity=entity, action=action, permission=permission, risk_tier=risk)(
        endpoint
    )


for _method, _path, _entity, _action, _permission, _risk, _status in _ROUTES:
    router.add_api_route(
        _path,
        _make_endpoint(_entity, _action, _permission, _risk, _method, _status),
        methods=[_method],
        status_code=_status,
    )
