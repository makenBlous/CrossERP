# ruff: noqa: B008
"""我的账户 JSON API。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers.platform import (
    _dispatch_write,
    _page,
    _principal_db,
    _user,
    _write_guard,
)
from crosserp.api.schemas import CamelModel, PageParams
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import verify_password
from crosserp.auth.tokens import create_token, revoke_token
from crosserp.db.repo.users import set_password
from crosserp.db.schema import ApiToken, AppSetting, UserSession
from crosserp.platform.dispatcher import RiskTier

router = APIRouter()


class ProfilePatch(CamelModel):
    display_name: str = ""
    locale: str = ""
    timezone: str = ""


class PasswordChange(CamelModel):
    current_password: str
    new_password: str


class TokenCreate(CamelModel):
    name: str = "token"


class ActionInput(CamelModel):
    pass


def _profile_preferences(session: Session, user_id: UUID) -> dict[str, str]:
    setting = session.get(AppSetting, f"account_profile:{user_id}")
    if setting is None:
        return {"locale": "zh-CN", "timezone": "Asia/Shanghai"}
    return dict(setting.value_json)


@router.get("/account/profile")
@api_endpoint(
    entity="UserAccount", action="UserAccount.list", permission="user:read", risk_tier="none"
)
def profile(request: Request, params: PageParams = Depends()) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        user = _user(session, principal.user_id)
        preferences = _profile_preferences(session, user.id)
        item = {
            "userId": str(user.id),
            "username": user.username,
            "displayName": user.display_name,
            "locale": preferences["locale"],
            "timezone": preferences["timezone"],
        }
        return _page(params, [item], 1)
    finally:
        session.close()


@router.patch("/account/profile")
@api_endpoint(
    entity="UserAccount", action="UserAccount.update", permission="user:write", risk_tier="critical"
)
def update_profile(
    request: Request,
    payload: ProfilePatch = ProfilePatch(),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        setting = session.get(AppSetting, f"account_profile:{user.id}")

        def work() -> dict[str, Any]:
            preferences = _profile_preferences(session, user.id)
            if "display_name" in payload.model_fields_set:
                user.display_name = payload.display_name
            if "locale" in payload.model_fields_set:
                preferences["locale"] = payload.locale
            if "timezone" in payload.model_fields_set:
                preferences["timezone"] = payload.timezone
            if setting is None:
                session.add(
                    AppSetting(
                        key=f"account_profile:{user.id}",
                        value_json=preferences,
                        updated_by=user.id,
                        updated_at=datetime.now(UTC),
                    )
                )
            else:
                setting.value_json = preferences
                setting.updated_by = user.id
                setting.updated_at = datetime.now(UTC)
            record_security(
                session,
                SecurityEventName.PROFILE_UPDATED,
                user_id=user.id,
                username=user.username,
                detail={"fields": sorted(payload.model_fields_set)},
            )
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
    request: Request,
    payload: PasswordChange,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        if not verify_password(user.password_hash, payload.current_password):
            raise APIError(ErrorCode.AUTH_REQUIRED, "当前密码错误", status_code=401)

        def work() -> dict[str, Any]:
            set_password(session, user.id, payload.new_password)
            current_cookie = request.cookies.get("crosserp_session")
            current_id = (
                hashlib.sha256(current_cookie.encode()).hexdigest() if current_cookie else None
            )
            now = datetime.now(UTC)
            for active in session.scalars(
                select(UserSession).where(
                    UserSession.user_id == user.id, UserSession.revoked_at.is_(None)
                )
            ):
                if active.id != current_id:
                    active.revoked_at = now
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
                "id": str(row.id),
                "name": row.name,
                "prefix": "cerp_",
                "createdAt": row.created_at.isoformat(),
                "lastUsedAt": row.last_used_at.isoformat() if row.last_used_at else None,
                "revokedAt": row.revoked_at.isoformat() if row.revoked_at else None,
            }
            for row in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.post("/account/tokens")
@api_endpoint(
    entity="ApiToken", action="ApiToken.create", permission="user:write", risk_tier="critical"
)
def create_api_token(
    request: Request,
    payload: TokenCreate = TokenCreate(),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        user = _user(session, principal.user_id)
        issued: dict[str, Any] = {}

        def work() -> ApiToken:
            row, plain = create_token(session, user, name=payload.name)
            issued["row"] = row
            issued["plain"] = plain
            return row

        _dispatch_write(
            request,
            principal,
            session,
            permission="user:write",
            risk=RiskTier.CRITICAL,
            entity="ApiToken",
            action="ApiToken.create",
            work=work,
        )
        session.commit()
        row = cast(ApiToken, issued["row"])
        return {
            "id": str(row.id),
            "name": row.name,
            "token": cast(str, issued["plain"]),
            "status": "created",
        }
    finally:
        session.close()


@router.post("/account/tokens/{id}/revoke")
@api_endpoint(
    entity="ApiToken", action="ApiToken.revoke", permission="user:write", risk_tier="critical"
)
def revoke_api_token(
    request: Request,
    id: UUID,
    payload: ActionInput = ActionInput(),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    del payload
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
        current_digest = hashlib.sha256(request.cookies["crosserp_session"].encode()).hexdigest()
        items = [
            {
                "id": row.id[:16],
                "createdAt": row.created_at.isoformat(),
                "expiresAt": row.expires_at.isoformat(),
                "lastSeenAt": row.last_seen_at.isoformat(),
                "revokedAt": row.revoked_at.isoformat() if row.revoked_at else None,
                "current": row.id == current_digest,
            }
            for row in rows
        ]
        return _page(params, items, len(items))
    finally:
        session.close()


@router.delete("/account/sessions/{id}")
@api_endpoint(
    entity="UserAccount", action="UserAccount.delete", permission="user:write", risk_tier="critical"
)
def kick_session(
    request: Request,
    id: str,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        current_digest = hashlib.sha256(request.cookies["crosserp_session"].encode()).hexdigest()
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
            session,
            SecurityEventName.LOGOUT,
            user_id=principal.user_id,
            detail={"kicked": id},
        )
        session.commit()
        return {"id": id, "status": "revoked", "current": target.id == current_digest}
    finally:
        session.close()
