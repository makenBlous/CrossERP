# ruff: noqa: B008
"""P0 平台底座 JSON API。所有写入复用底座的动作执行器和审计协议。"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import PageParams
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import hash_password, verify_password
from crosserp.auth.permissions import ROLE_PERMISSIONS
from crosserp.auth.roles import Role
from crosserp.auth.sessions import create_session, revoke_session
from crosserp.auth.tokens import create_token, revoke_token
from crosserp.config import load_settings
from crosserp.db.repo.users import get_by_username, set_password
from crosserp.db.schema import (
    ApiToken,
    AppSetting,
    AppUser,
    FileObject,
    Job,
    PasswordResetToken,
    Store,
    UserRole,
    UserSession,
)
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal, get_principal
from crosserp.platform.session_events import on_session_revoked

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


@router.post("/auth/login")
@api_endpoint(
    entity="UserAccount", action="UserAccount.login", permission="public", risk_tier="critical"
)
def login(request: Request, payload: dict[str, Any]) -> JSONResponse:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    now = datetime.now(UTC)
    settings = load_settings().auth
    with _db(request) as session:
        user = get_by_username(session, username)
        valid = verify_password(
            user.password_hash if user else hash_password("dummy-login-password"), password
        )
        locked = bool(user and user.locked_until and user.locked_until > now)
        if user is None or not user.is_active or locked or not valid:
            if user is not None and not locked:
                user.failed_logins += 1
                if user.failed_logins >= settings.max_failed_logins:
                    user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            record_security(
                session,
                SecurityEventName.LOGIN_FAILED,
                user_id=user.id if user else None,
                username=username,
            )
            session.commit()
            raise APIError(ErrorCode.AUTH_REQUIRED, "账号或密码错误", status_code=401)
        user.failed_logins = 0
        user.locked_until = None
        token = create_session(
            session,
            user,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            hours=settings.session_hours,
        )
        record_security(
            session, SecurityEventName.LOGIN_SUCCESS, user_id=user.id, username=user.username
        )
        roles = frozenset(session.scalars(select(UserRole.role).where(UserRole.user_id == user.id)))
        principal = Principal(
            user_id=user.id, roles=roles, permissions=_effective_permissions(roles)
        )
        session.commit()
    response = JSONResponse(_user_payload(session, user, principal, token.csrf_token))
    secure = load_settings().cookie_secure or request.url.scheme == "https"
    response.set_cookie(
        "crosserp_session", token.value, httponly=True, samesite="lax", secure=secure, path="/"
    )
    response.set_cookie(
        "crosserp_csrf", token.csrf_token, httponly=False, samesite="lax", secure=secure, path="/"
    )
    return response


@router.post("/auth/logout")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.logout",
    permission="authenticated",
    risk_tier="critical",
)
def logout(
    request: Request, csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        _require(principal, "authenticated", entity="UserAccount")
        token = request.cookies.get("crosserp_session")

        def work() -> dict[str, Any]:
            revoke_session(session, token)
            on_session_revoked(session, token, reason="logout")
            record_security(session, SecurityEventName.LOGOUT, user_id=principal.user_id)
            return {"id": str(principal.user_id), "status": "logged_out"}

        result = _dispatch_write(
            request,
            principal,
            session,
            permission="authenticated",
            risk=RiskTier.CRITICAL,
            entity="UserAccount",
            action="UserAccount.logout",
            work=work,
        )
        session.commit()
        return dict(result)
    finally:
        session.close()


@router.get("/auth/me")
@api_endpoint(
    entity="UserAccount", action="UserAccount.read_me", permission="authenticated", risk_tier="none"
)
def me(request: Request) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        user = session.get(AppUser, principal.user_id)
        return (
            _user_payload(session, user, principal, request.cookies.get("crosserp_csrf"))
            if user
            else (_ for _ in ()).throw(not_found())
        )
    finally:
        session.close()


@router.post("/auth/forgot-password")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.forgot_password",
    permission="public",
    risk_tier="critical",
)
def forgot_password(request: Request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    username = str((payload or {}).get("username", "")).strip()
    with _db(request) as session:
        user = get_by_username(session, username)
        result: dict[str, Any] = {"status": "accepted"}
        if user:
            plain = secrets.token_urlsafe(32)
            session.add(
                PasswordResetToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=hashlib.sha256(plain.encode()).hexdigest(),
                    created_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            result["resetToken"] = plain
        session.commit()
        return result


@router.post("/auth/reset-password")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.reset_password",
    permission="public",
    risk_tier="critical",
)
def reset_password(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    plain = str(payload.get("token", ""))
    new_password = str(payload.get("newPassword", payload.get("password", "")))
    digest = hashlib.sha256(plain.encode()).hexdigest()
    with _db(request) as session:
        row = session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == digest, PasswordResetToken.used_at.is_(None)
            )
        )
        if row is None or row.expires_at <= datetime.now(UTC):
            raise APIError(ErrorCode.AUTH_REQUIRED, "重置令牌无效", status_code=401)
        set_password(session, row.user_id, new_password)
        row.used_at = datetime.now(UTC)
        for active in session.scalars(
            select(UserSession).where(
                UserSession.user_id == row.user_id, UserSession.revoked_at.is_(None)
            )
        ):
            active.revoked_at = datetime.now(UTC)
        session.commit()
        return {"id": str(row.user_id), "status": "password_reset"}


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


@router.get("/me/data-scope")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.read_data_scope",
    permission="user:read",
    risk_tier="none",
)
def data_scope(request: Request) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        return {"scopes": [principal.data_scope or {}]}
    finally:
        session.close()


@router.post("/files", status_code=201)
@api_endpoint(
    entity="FileObject", action="FileObject.create", permission="authenticated", risk_tier="low"
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        content = await file.read()
        digest = hashlib.sha256(content).hexdigest()
        existing = session.scalar(select(FileObject).where(FileObject.sha256 == digest))
        if existing:
            return {"id": str(existing.id), "sha256": digest, "status": "deduplicated"}
        root = Path(os.environ.get("CROSSERP_FILES_DIR", "var/files"))
        root.mkdir(parents=True, exist_ok=True)
        path = root / digest
        path.write_bytes(content)
        row = FileObject(
            id=uuid4(),
            sha256=digest,
            filename=file.filename or "upload",
            content_type=file.content_type,
            size=len(content),
            storage_path=str(path),
            uploaded_by=principal.user_id,
            created_at=datetime.now(UTC),
        )
        session.add(row)
        _dispatch_write(
            request,
            principal,
            session,
            permission="authenticated",
            risk=RiskTier.LOW,
            entity="FileObject",
            action="FileObject.create",
            work=lambda: row,
        )
        session.commit()
        return {
            "id": str(row.id),
            "sha256": digest,
            "filename": row.filename,
            "size": row.size,
            "status": "created",
        }
    finally:
        session.close()


@router.get("/files/{id}")
@api_endpoint(
    entity="FileObject", action="FileObject.get", permission="authenticated", risk_tier="none"
)
def get_file(request: Request, id: UUID) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        row = session.get(FileObject, id)
        if row is None or row.uploaded_by != principal.effective_user_id:
            raise not_found()
        return {
            "id": str(row.id),
            "sha256": row.sha256,
            "filename": row.filename,
            "contentType": row.content_type,
            "size": row.size,
            "createdAt": row.created_at.isoformat(),
        }
    finally:
        session.close()


@router.get("/jobs/{id}")
@api_endpoint(entity="Job", action="Job.get", permission="authenticated", risk_tier="none")
def get_job(request: Request, id: UUID) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        row = session.get(Job, id)
        if row is None or row.created_by != principal.effective_user_id:
            raise not_found()
        return {
            "id": str(row.id),
            "kind": row.kind,
            "status": row.status,
            "progress": row.progress,
            "error": row.error,
            "resultRef": row.result_ref,
            "createdBy": str(row.created_by),
            "createdAt": row.created_at.isoformat(),
        }
    finally:
        session.close()


@router.get("/stores")
@api_endpoint(entity="Store", action="Store.list", permission="report:read", risk_tier="none")
def list_stores(
    request: Request, params: PageParams = Depends(), q: str | None = Query(None)
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        statement = select(Store).order_by(Store.name)
        scope = principal.data_scope or {}
        ids = scope.get("storeIds") if isinstance(scope, dict) else None
        if ids and "all" not in scope:
            statement = statement.where(Store.id.in_([UUID(str(v)) for v in ids]))
        if q:
            statement = statement.where(Store.name.contains(q))
        rows = list(session.scalars(statement))
        items = [
            {
                "id": str(r.id),
                "platform": r.platform,
                "marketplace": r.marketplace,
                "name": r.name,
                "currency": r.currency,
            }
            for r in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.post("/admin/stores", status_code=201)
@api_endpoint(
    entity="Store", action="Store.create", permission="system:write", risk_tier="critical"
)
def create_store(
    request: Request, payload: dict[str, Any], csrf: str | None = Header(None, alias="X-CSRF-Token")
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        row = Store(
            id=uuid4(),
            platform=str(payload.get("platform", "")),
            marketplace=str(payload.get("marketplace", "")),
            name=str(payload.get("name", "")),
            currency=str(payload.get("currency", "CNY")).upper(),
        )
        session.add(row)
        _dispatch_write(
            request,
            principal,
            session,
            permission="system:write",
            risk=RiskTier.CRITICAL,
            entity="Store",
            action="Store.create",
            work=lambda: row,
        )
        session.commit()
        return {"id": str(row.id), "status": "created", "version": 1}
    finally:
        session.close()


@router.patch("/admin/stores/{id}")
@api_endpoint(
    entity="Store", action="Store.update", permission="system:write", risk_tier="critical"
)
def update_store(
    request: Request,
    id: UUID,
    payload: dict[str, Any],
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        row = session.get(Store, id)
        if row is None:
            raise not_found()

        def work() -> dict[str, Any]:
            for key in ("platform", "marketplace", "name", "currency"):
                if key in payload:
                    setattr(
                        row,
                        key,
                        str(payload[key]).upper() if key == "currency" else str(payload[key]),
                    )
            return {"id": str(row.id), "status": "updated", "version": 1}

        result = _dispatch_write(
            request,
            principal,
            session,
            permission="system:write",
            risk=RiskTier.CRITICAL,
            entity="Store",
            action="Store.update",
            work=work,
        )
        session.commit()
        return cast(dict[str, Any], result)
    finally:
        session.close()


__all__ = ["router"]
