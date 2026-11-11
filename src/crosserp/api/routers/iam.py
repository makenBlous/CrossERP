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
from crosserp.db.schema import (
    AppUser,
    IamAccessReview,
    IamDataScopeRule,
    IamDictionary,
    IamFieldPolicy,
    IamModuleSwitch,
    IamPermissionOverride,
    IamRole,
    IamSodRule,
    IamSystemSetting,
    IamTemporaryGrant,
    UserRole,
)
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

    ActionDispatcher().dispatch(
        principal=principal,
        permission=permission,
        risk_tier=risk,
        action=permission,
        business_action=lambda: None,
        hooks={"permission": check_permission},
    )


def _result(data: Any, *, created: bool = False) -> dict[str, Any]:
    return {"data": data, "status": "created" if created else "ok"}


def _audit(request: Request, principal: Principal, entity: str, action: str, diff: Any) -> None:
    with _session(request) as session, session.begin():
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity=entity,
            action=action,
            diff=diff,
            request_id=request.state.request_id,
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
                request_id=request.state.request_id,
                detail={"entity": entity, "action": action, "diff": diff},
            )


def _record(obj: AppUser) -> dict[str, Any]:
    return {
        "id": str(obj.id),
        "username": obj.username,
        "displayName": obj.display_name,
        "isActive": obj.is_active,
        "permissionVersion": obj.permission_version,
    }


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
            user = _get_user(session, path_id) if path_id is not None else None
            if method == "GET":
                return _record(user)
            if method == "POST" and path_id is None:
                username = _required_string(payload, "username")
                password = _required_string(payload, "password")
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
                return _result({"id": str(user.id), "roles": sorted(roles)})
            if action == "User.set_overrides":
                session.query(IamPermissionOverride).filter(
                    IamPermissionOverride.user_id == user.id
                ).delete(synchronize_session=False)
                for item in payload.get("overrides", []):
                    if isinstance(item, dict) and item.get("permission"):
                        session.add(
                            IamPermissionOverride(
                                user_id=user.id,
                                permission=str(item["permission"]),
                                effect="deny" if item.get("effect") == "deny" else "allow",
                                reason=str(item.get("reason", "user override")),
                                data_scopes=item.get("dataScopes", []),
                                starts_at=None,
                                expires_at=None,
                                created_at=datetime.now(UTC),
                            )
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
        role = iam.roles.get(path_id)
        if role is None:
            raise not_found()
        if method == "GET":
            return {
                "id": role.id,
                "name": role.name or role.id,
                "parentIds": sorted(role.parent_ids),
                "permissions": role.permissions,
                "dataScopes": sorted(role.data_scopes),
                "active": role.active,
            }
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
            role = iam.update_role(
                path_id,
                parent_ids=set(payload["parentIds"]) if "parentIds" in payload else None,
                permissions=(
                    {str(k): str(v) for k, v in payload["permissions"].items()}
                    if "permissions" in payload
                    else None
                ),
                active=bool(payload["active"]) if "active" in payload else None,
            )
        if action == "Role.set_permissions":
            role = iam.update_role(
                path_id,
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
    if entity == "TempGrant":
        if method == "GET":
            with _session(request) as session:
                rows = list(session.scalars(select(IamTemporaryGrant)))
            return {"items": [_model_record(row) for row in rows], "total": len(rows)}
        if method == "POST" and path_id is None:
            if "userId" not in payload:
                raise APIError(ErrorCode.VALIDATION_FAILED, "userId 必填")
            try:
                user_id = UUID(str(payload["userId"]))
            except ValueError as exc:
                raise APIError(ErrorCode.VALIDATION_FAILED, "userId 无效") from exc
            raw_expires = payload.get("expiresAt")
            try:
                expires_at = (
                    datetime.fromisoformat(str(raw_expires))
                    if "expiresAt" in payload
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
            with _session(request) as session:
                stored = session.scalar(
                    select(IamTemporaryGrant)
                    .where(
                        IamTemporaryGrant.user_id == user_id,
                        IamTemporaryGrant.permission == grant.permission,
                    )
                    .order_by(IamTemporaryGrant.created_at.desc())
                )
            if stored is None:
                raise APIError(ErrorCode.INTERNAL_ERROR, "临时授权写入失败")
            result = _result(
                {
                    "id": str(stored.id),
                    "userId": str(user_id),
                    "permission": grant.permission,
                },
                created=True,
            )
            _audit(request, principal, entity, action, result)
            return result
    if entity == "PermissionPoint" and action == "PermissionPoint.update":
        cells = payload.get("cells")
        if not isinstance(cells, list):
            raise APIError(ErrorCode.VALIDATION_FAILED, "cells 必须是数组")
        for cell in cells:
            if not isinstance(cell, dict):
                raise APIError(ErrorCode.VALIDATION_FAILED, "权限格格式无效")
            role_id = _required_string(cell, "roleId")
            permission_key = _required_string(cell, "permissionKey")
            effect = cell.get("effect")
            if effect not in {"allow", "deny"}:
                raise APIError(ErrorCode.VALIDATION_FAILED, "权限格 effect 无效")
            role = iam.roles.get(role_id)
            if role is None:
                raise not_found()
            permissions = dict(role.permissions)
            permissions[permission_key] = effect
            iam.update_role(role_id, permissions=permissions)
        result = _result({"cells": cells})
        _audit(request, principal, entity, action, result)
        return result
    model_map = {
        "FieldPolicy": IamFieldPolicy,
        "DataScopeRule": IamDataScopeRule,
        "AccessReview": IamAccessReview,
        "SodRule": IamSodRule,
        "ModuleSwitch": IamModuleSwitch,
        "Dictionary": IamDictionary,
        "SystemSetting": IamSystemSetting,
    }
    if entity in model_map:
        model = model_map[entity]
        with _session(request) as session:
            if method == "GET":
                rows = list(session.scalars(select(model)))
                return {
                    "items": [_model_record(row) for row in rows],
                    "page": 1,
                    "pageSize": len(rows),
                    "total": len(rows),
                }
            if entity == "Dictionary":
                row = session.get(model, path_key)
            elif entity == "ModuleSwitch":
                row = session.get(model, path_id)
            elif entity == "SystemSetting":
                row = session.get(model, "system")
            else:
                row = None
                if path_id is not None:
                    try:
                        row = session.get(model, UUID(path_id))
                    except ValueError:
                        row = None
            if row is None:
                if entity == "AccessReview" and method == "POST":
                    row = model(
                        user_id=UUID(str(payload.get("userId", principal.effective_user_id))),
                        state="open",
                        snapshot=payload.get("snapshot", {}),
                        created_at=datetime.now(UTC),
                    )
                    session.add(row)
                elif entity == "FieldPolicy" and method in {"PUT", "PATCH"}:
                    row = model(
                        id=UUID(path_id),
                        field_key=str(payload.get("fieldKey", path_id)),
                        permission=str(payload.get("permission", "permission:read")),
                        masked=bool(payload.get("masked", False)),
                        updated_at=datetime.now(UTC),
                    )
                    session.add(row)
                elif entity == "DataScopeRule" and method in {"PUT", "PATCH"}:
                    row = model(
                        id=UUID(path_id),
                        name=str(payload.get("name", path_id)),
                        entity=str(payload.get("entity", "*")),
                        scope_type=str(payload.get("scopeType", "store")),
                        values=payload.get("values", []),
                        updated_at=datetime.now(UTC),
                    )
                    session.add(row)
                elif entity == "SodRule" and method in {"PUT", "PATCH"}:
                    row = model(
                        id=UUID(path_id),
                        name=str(payload.get("name", path_id)),
                        permissions=payload.get("permissions", []),
                        enabled=bool(payload.get("enabled", True)),
                        updated_at=datetime.now(UTC),
                    )
                    session.add(row)
                elif method in {"PUT", "PATCH"} and entity in {
                    "Dictionary",
                    "ModuleSwitch",
                    "SystemSetting",
                }:
                    if entity == "Dictionary":
                        row = model(
                            key=path_key,
                            values=payload.get("values", []),
                            updated_at=datetime.now(UTC),
                        )
                    elif entity == "ModuleSwitch":
                        row = model(
                            module=path_id,
                            enabled=bool(payload.get("enabled", True)),
                            config=payload.get("config", {}),
                            updated_at=datetime.now(UTC),
                        )
                    else:
                        row = model(key="system", value=payload, updated_at=datetime.now(UTC))
                    session.add(row)
                else:
                    raise not_found()
            if entity == "AccessReview" and action == "AccessReview.confirm":
                row.state = "confirmed"
                row.reviewed_by = principal.effective_user_id
                row.reviewed_at = datetime.now(UTC)
            field_aliases = {
                "FieldPolicy": {
                    "fieldKey": "field_key",
                    "permission": "permission",
                    "masked": "masked",
                    "updatedBy": "updated_by",
                },
                "DataScopeRule": {
                    "name": "name",
                    "entity": "entity",
                    "scopeType": "scope_type",
                    "values": "values",
                    "updatedBy": "updated_by",
                },
                "SodRule": {
                    "name": "name",
                    "permissions": "permissions",
                    "enabled": "enabled",
                    "updatedBy": "updated_by",
                },
                "ModuleSwitch": {
                    "enabled": "enabled",
                    "config": "config",
                    "updatedBy": "updated_by",
                },
                "Dictionary": {"values": "values", "updatedBy": "updated_by"},
                "SystemSetting": {"value": "value", "updatedBy": "updated_by"},
                "AccessReview": {"snapshot": "snapshot"},
            }[entity]
            for key, value in payload.items():
                attr = field_aliases.get(key)
                if attr is not None:
                    setattr(row, attr, value)
            session.commit()
            result = _result(_model_record(row))
        _audit(request, principal, entity, action, result)
        return result
    if entity == "TempGrant" and method == "POST" and path_id:
        try:
            grant_id = UUID(path_id)
        except ValueError as exc:
            raise not_found() from exc
        with _session(request) as session:
            grant = session.get(IamTemporaryGrant, grant_id)
            if grant is None:
                raise not_found()
            grant.revoked_at = datetime.now(UTC)
            user = session.get(AppUser, grant.user_id)
            if user is None:
                raise APIError(ErrorCode.INTERNAL_ERROR, "临时授权所属用户不存在")
            user.permission_version += 1
            session.commit()
        result = _result({"id": path_id, "revoked": True})
        _audit(request, principal, entity, action, result)
        return result
    raise APIError(ErrorCode.INTERNAL_ERROR, f"未处理的 IAM 动作: {entity}.{action}")


def _get_user(session: Session, value: str) -> AppUser:
    try:
        user = session.get(AppUser, UUID(value))
    except ValueError:
        user = None
    if user is None:
        raise not_found()
    return user


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{key} 必填")
    return value.strip()


def _model_record(row: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        values[column.name] = str(value) if isinstance(value, UUID) else value
    return values


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
