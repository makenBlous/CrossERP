# ruff: noqa: B008, RUF059
"""P0 平台底座 JSON API。所有写入复用底座的动作执行器和审计协议。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import PageParams
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import verify_password
from crosserp.auth.permissions import ROLE_PERMISSIONS
from crosserp.auth.roles import Role
from crosserp.auth.tokens import create_token, revoke_token
from crosserp.db.repo.users import set_password
from crosserp.db.schema import (
    ApiToken,
    AppSetting,
    AppUser,
    DocumentLink,
    UserRole,
    UserSession,
)
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()
_permission_service = DefaultPermissionService()
_dispatcher = ActionDispatcher()


def _engine(request: Request) -> Any:
    return request.app.state.database_engine


def _db(request: Request) -> Session:
    return Session(_engine(request), expire_on_commit=False)


def _principal_db(request: Request) -> tuple[Principal, Session]:
    principal = get_principal(request)
    session = _db(request)
    user = session.get(AppUser, principal.user_id) if principal.user_id else None
    if user is None or not user.is_active:
        session.close()
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    roles = frozenset(
        r.role for r in session.scalars(select(UserRole).where(UserRole.user_id == user.id))
    )
    scope = _scope(session, user.id, roles)
    return Principal(
        user_id=user.id,
        roles=roles,
        session_id=principal.session_id,
        actor_type=principal.actor_type,
        agent_id=principal.agent_id,
        on_behalf_of=principal.on_behalf_of,
        delegation_id=principal.delegation_id,
        run_id=principal.run_id,
        is_subagent=principal.is_subagent,
        channel=principal.channel,
        permissions=_effective_permissions(roles),
        data_scope=scope,
    ), session


def _effective_permissions(roles: frozenset[str]) -> frozenset[str]:
    result = {p.value for role in roles for p in ROLE_PERMISSIONS.get(Role(role), frozenset())}
    if "admin" in roles:
        result.update({"user:read", "user:write", "system:write", "report:read", "document:read"})
    if roles & {"finance", "operator", "viewer", "auditor"}:
        result.update({"user:read", "report:read", "document:read"})
    if "operator" in roles or "finance" in roles:
        result.add("user:write")
    return frozenset(result)


def _scope(session: Session, user_id: UUID, roles: frozenset[str]) -> dict[str, Any]:
    if "admin" in roles:
        return {"all": True}
    setting = session.get(AppSetting, f"data_scope:{user_id}")
    if setting is None or not isinstance(setting.value_json, dict):
        return {}
    return dict(setting.value_json)


def _require(principal: Principal, permission: str, *, entity: str) -> None:
    _permission_service.require(principal, permission)


def _write_guard(request: Request, principal: Principal, csrf: str | None) -> None:
    cookie = request.cookies.get("crosserp_session")
    if (
        cookie
        and request.headers.get("Authorization", "").casefold().startswith("bearer ") is False
    ):
        expected = request.cookies.get("crosserp_csrf")
        if not csrf or not expected or not secrets.compare_digest(csrf, expected):
            raise APIError(ErrorCode.CSRF_INVALID, "CSRF 令牌无效", status_code=403)


def _dispatch_write(
    request: Request,
    principal: Principal,
    session: Session,
    *,
    permission: str,
    risk: RiskTier,
    entity: str,
    action: str,
    work: Any,
) -> Any:
    _require(principal, permission, entity=entity)
    result = _dispatcher.dispatch(
        principal=principal,
        permission=permission,
        risk_tier=risk,
        action=action,
        business_action=work,
    )
    DefaultAuditRecorder(session).record(
        principal=principal,
        entity=entity,
        action=action,
        diff={"result": _jsonable(result)},
        request_id=getattr(request.state, "request_id", None),
    )
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "id"):
        return str(value.id)
    return value


def _page(params: PageParams, items: list[Any], total: int) -> dict[str, Any]:
    return {"items": items, "page": params.page, "pageSize": params.page_size, "total": total}


def _user_payload(
    session: Session, user: AppUser, principal: Principal, csrf: str | None = None
) -> dict[str, Any]:
    roles = sorted(principal.roles)
    return {
        "userId": str(user.id),
        "displayName": user.display_name,
        "roles": roles,
        "permissions": sorted(principal.permissions),
        "dataScopes": [principal.data_scope or {}],
        "fieldPolicies": [],
        "aiMode": "normal",
        "locale": "zh-CN",
        "timezone": "Asia/Shanghai",
        "baseCurrency": "CNY",
        "csrfToken": csrf,
    }


def _user(session: Session, user_id: UUID | None) -> AppUser:
    row = session.get(AppUser, user_id) if user_id else None
    if row is None:
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录", status_code=401)
    return row


@router.get("/account/profile")
@api_endpoint(
    entity="UserAccount", action="UserAccount.list", permission="user:read", risk_tier="none"
)
def profile(request: Request, params: PageParams = Depends()) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        user = _user(session, principal.user_id)
        item = {
            "userId": str(user.id),
            "username": user.username,
            "displayName": user.display_name,
            "locale": "zh-CN",
            "timezone": "Asia/Shanghai",
        }
        return _page(params, [item], 1)
    finally:
        session.close()


@router.patch("/account/profile")
@api_endpoint(
    entity="UserAccount", action="UserAccount.update", permission="user:write", risk_tier="critical"
)
def update_profile(
    request: Request, payload: dict[str, Any], csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)

        def work() -> dict[str, Any]:
            if "displayName" in payload:
                user.display_name = str(payload["displayName"])[:128]
            return {"id": str(user.id), "status": "updated"}

        result = _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="UserAccount",
            action="UserAccount.update",
            work=work,
        )
        session.commit()
        return cast(dict[str, Any], result)
    finally:
        session.close()


@router.post("/account/password")
@api_endpoint(
    entity="UserAccount", action="UserAccount.create", permission="user:write", risk_tier="critical"
)
def change_password(
    request: Request, payload: dict[str, Any], csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        if not user or not verify_password(
            user.password_hash, str(payload.get("currentPassword", ""))
        ):
            raise APIError(ErrorCode.AUTH_REQUIRED, "当前密码错误", status_code=401)

        def work() -> dict[str, Any]:
            set_password(session, user.id, str(payload.get("newPassword", "")))
            record_security(session, SecurityEventName.PASSWORD_CHANGED, user_id=user.id)
            return {"id": str(user.id), "status": "updated"}

        result = _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="UserAccount",
            action="UserAccount.create",
            work=work,
        )
        session.commit()
        return cast(dict[str, Any], result)
    finally:
        session.close()


@router.get("/account/tokens")
@api_endpoint(entity="ApiToken", action="ApiToken.list", permission="user:read", risk_tier="none")
def tokens(request: Request, params: PageParams = Depends()) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        rows = list(
            session.scalars(
                select(ApiToken)
                .where(ApiToken.user_id == principal.user_id)
                .order_by(ApiToken.created_at.desc())
            )
        )
        items = [
            {
                "id": str(r.id),
                "name": r.name,
                "createdAt": r.created_at.isoformat(),
                "lastUsedAt": r.last_used_at.isoformat() if r.last_used_at else None,
                "revokedAt": r.revoked_at.isoformat() if r.revoked_at else None,
            }
            for r in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.post("/account/tokens")
@api_endpoint(
    entity="ApiToken", action="ApiToken.create", permission="user:write", risk_tier="critical"
)
def create_api_token(
    request: Request, payload: dict[str, Any], csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        token_plain = _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="ApiToken",
            action="ApiToken.create",
            work=lambda: create_token(session, user, name=str(payload.get("name", "token")))[1],
        )
        row = session.scalar(
            select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
        )
        if row is None:
            raise APIError(ErrorCode.INTERNAL_ERROR, "Token 创建失败")
        session.commit()
        return {"id": str(row.id), "name": row.name, "token": token_plain, "status": "created"}
    finally:
        session.close()


@router.post("/account/tokens/{id}/revoke")
@api_endpoint(
    entity="ApiToken", action="ApiToken.revoke", permission="user:write", risk_tier="critical"
)
def revoke_api_token(
    request: Request, id: UUID, csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        result = _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="ApiToken",
            action="ApiToken.revoke",
            work=lambda: revoke_token(session, id, user),
        )
        if not result:
            raise not_found()
        session.commit()
        return {"id": str(id), "status": "revoked"}
    finally:
        session.close()


@router.get("/account/sessions")
@api_endpoint(
    entity="UserAccount", action="UserAccount.list", permission="user:read", risk_tier="none"
)
def sessions(request: Request, params: PageParams = Depends()) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        rows = list(
            session.scalars(
                select(UserSession)
                .where(UserSession.user_id == principal.user_id)
                .order_by(UserSession.created_at.desc())
            )
        )
        items = [
            {
                "id": r.id[:16],
                "createdAt": r.created_at.isoformat(),
                "expiresAt": r.expires_at.isoformat(),
                "lastSeenAt": r.last_seen_at.isoformat(),
                "revokedAt": r.revoked_at.isoformat() if r.revoked_at else None,
                "current": r.id
                == hashlib.sha256(request.cookies.get("crosserp_session", "").encode()).hexdigest(),
            }
            for r in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.delete("/account/sessions/{id}")
@api_endpoint(
    entity="UserAccount", action="UserAccount.delete", permission="user:write", risk_tier="critical"
)
def kick_session(
    request: Request, id: str, csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        digest = hashlib.sha256(request.cookies.get("crosserp_session", "").encode()).hexdigest()
        target = session.scalar(
            select(UserSession).where(
                UserSession.user_id == principal.user_id, UserSession.id.like(f"{id}%")
            )
        )
        if target is None:
            raise not_found()
        _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="UserAccount",
            action="UserAccount.delete",
            work=lambda: setattr(target, "revoked_at", datetime.now(UTC)),
        )
        record_security(
            session, SecurityEventName.LOGOUT, user_id=principal.user_id, detail={"kicked": id}
        )
        session.commit()
        return {"id": id, "status": "revoked", "current": target.id == digest}
    finally:
        session.close()


@router.get("/documents/links")
@api_endpoint(
    entity="DocumentLink",
    action="DocumentLink.read_links",
    permission="document:read",
    risk_tier="none",
)
def links(request: Request, params: PageParams = Depends()) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        rows = list(session.scalars(select(DocumentLink).order_by(DocumentLink.created_at.desc())))
        items = [
            {
                "id": str(r.id),
                "from": {"type": r.from_type, "id": r.from_id},
                "to": {"type": r.to_type, "id": r.to_id},
                "relation": r.relation,
            }
            for r in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.get("/documents/chain/{docType}/{id}")
@api_endpoint(
    entity="DocumentLink",
    action="DocumentLink.read_chain",
    permission="report:read",
    risk_tier="none",
)
def chain(request: Request, docType: str, id: str) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        rows = list(
            session.scalars(
                select(DocumentLink).where(
                    (DocumentLink.from_type == docType) & (DocumentLink.from_id == id)
                    | (DocumentLink.to_type == docType) & (DocumentLink.to_id == id)
                )
            )
        )
        return {
            "entity": {"type": docType, "id": id},
            "links": [
                {
                    "id": str(r.id),
                    "fromType": r.from_type,
                    "fromId": r.from_id,
                    "toType": r.to_type,
                    "toId": r.to_id,
                    "relation": r.relation,
                }
                for r in rows
            ],
        }
    finally:
        session.close()


__all__ = ["router"]
