"""登录、会话和密码恢复 JSON API。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import (
    _db,
    _dispatch_write,
    _principal_db,
    _user_payload,
    _write_guard,
)
from crosserp.api.schemas import CamelModel
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import hash_password, verify_password
from crosserp.auth.sessions import create_session, revoke_session
from crosserp.config import load_settings
from crosserp.db.repo.users import get_by_username, set_password
from crosserp.db.schema import AppUser, PasswordResetToken, UserRole, UserSession
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.principal import Principal
from crosserp.platform.session_events import on_session_revoked

router = APIRouter()


class LoginInput(CamelModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class LogoutInput(CamelModel):
    pass


class ForgotPasswordInput(CamelModel):
    username: str = Field(min_length=1, max_length=64)


class ResetPasswordInput(CamelModel):
    token: str = Field(min_length=1)
    new_password: str = Field(alias="newPassword", min_length=1)


@router.post("/auth/login")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.login",
    permission="public",
    risk_tier="critical",
    idempotency="none",
)
def login(request: Request, payload: LoginInput) -> JSONResponse:
    now = datetime.now(UTC)
    settings = load_settings().auth
    with _db(request) as session:
        user = get_by_username(session, payload.username.strip())
        valid = verify_password(
            user.password_hash if user else hash_password("dummy-login-password"), payload.password
        )
        locked = user is not None and user.locked_until is not None and user.locked_until > now
        if user is None or not user.is_active or locked or not valid:
            if user is not None and not locked:
                user.failed_logins += 1
                if user.failed_logins >= settings.max_failed_logins:
                    user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            record_security(
                session,
                SecurityEventName.LOGIN_FAILED,
                user_id=user.id if user else None,
                username=payload.username,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_id=request.state.request_id,
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
            session,
            SecurityEventName.LOGIN_SUCCESS,
            user_id=user.id,
            username=user.username,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request.state.request_id,
        )
        session.commit()
        user_roles = frozenset(
            session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))
        )
        principal = Principal(
            user_id=user.id,
            roles=user_roles,
            permissions=request.app.state.permission_service.current_permissions(
                Principal(user_id=user.id, roles=user_roles)
            ),
        )
        payload_out = _user_payload(request, session, user, principal, token.csrf_token)

    response = JSONResponse(payload_out)
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
    idempotency="dispatcher",
)
def logout(
    request: Request,
    payload: LogoutInput | None = None,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> JSONResponse:
    del payload
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        token = request.cookies.get("crosserp_session")

        def work() -> dict[str, Any]:
            revoke_session(session, token)
            on_session_revoked(session, token, reason="logout")
            record_security(
                session,
                SecurityEventName.LOGOUT,
                user_id=principal.user_id,
                request_id=request.state.request_id,
            )
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
    finally:
        session.close()

    response = JSONResponse(dict(result))
    response.delete_cookie("crosserp_session", path="/")
    response.delete_cookie("crosserp_csrf", path="/")
    return response


@router.get("/auth/me")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.read_me",
    permission="authenticated",
    risk_tier="none",
    idempotency="none",
)
def me(request: Request) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        user = session.get(AppUser, principal.user_id)
        if user is None:
            raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录", status_code=401)
        return _user_payload(
            request, session, user, principal, request.cookies.get("crosserp_csrf")
        )
    finally:
        session.close()


@router.post("/auth/forgot-password")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.forgot_password",
    permission="public",
    risk_tier="critical",
    idempotency="none",
)
def forgot_password(request: Request, payload: ForgotPasswordInput) -> dict[str, Any]:
    with _db(request) as session:
        user = get_by_username(session, payload.username.strip())
        result: dict[str, Any] = {"status": "accepted"}
        if user is not None:
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
    idempotency="none",
)
def reset_password(request: Request, payload: ResetPasswordInput) -> dict[str, Any]:
    digest = hashlib.sha256(payload.token.encode()).hexdigest()
    with _db(request) as session:
        row = session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == digest, PasswordResetToken.used_at.is_(None)
            )
        )
        if row is None or row.expires_at <= datetime.now(UTC):
            raise APIError(ErrorCode.AUTH_REQUIRED, "重置令牌无效", status_code=401)
        set_password(session, row.user_id, payload.new_password)
        row.used_at = datetime.now(UTC)
        for active in session.scalars(
            select(UserSession).where(
                UserSession.user_id == row.user_id, UserSession.revoked_at.is_(None)
            )
        ):
            active.revoked_at = datetime.now(UTC)
        record_security(
            session,
            SecurityEventName.PASSWORD_RESET,
            user_id=row.user_id,
            request_id=request.state.request_id,
        )
        session.commit()
        return {"id": str(row.user_id), "status": "password_reset"}
