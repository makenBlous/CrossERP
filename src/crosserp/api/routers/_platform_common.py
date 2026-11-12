"""P0 平台底座 JSON API。所有写入复用底座的动作执行器和审计协议。"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.schemas import PageParams
from crosserp.db.schema import (
    ApiToken,
    AppUser,
    FileObject,
    Job,
    Store,
    UserRole,
)
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()


def _engine(request: Request) -> Any:
    return request.app.state.database_engine


def _db(request: Request) -> Session:
    return Session(_engine(request), expire_on_commit=False)


def _principal_db(
    request: Request, principal_override: Principal | None = None
) -> tuple[Principal, Session]:
    principal = get_principal(request) if principal_override is None else principal_override
    session = _db(request)
    user = session.get(AppUser, principal.user_id) if principal.user_id else None
    if user is None or not user.is_active:
        session.close()
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    roles = frozenset(
        r.role for r in session.scalars(select(UserRole).where(UserRole.user_id == user.id))
    )
    resolved = Principal(
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
        permissions=request.app.state.permission_service.current_permissions(principal),
        data_scope=request.app.state.permission_service.data_scope_filter(principal, "UserAccount"),
    )
    return resolved, session


def _require(request: Request, principal: Principal, permission: str, *, entity: str) -> None:
    request.app.state.permission_service.require(principal, permission)


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
    from crosserp.approval.gateway import ApprovalGatewayImpl
    from crosserp.platform.dispatcher import ActionDispatcher

    _require(request, principal, permission, entity=entity)
    result = ActionDispatcher(
        session=session,
        permission_service=request.app.state.permission_service,
        approval_gateway=ApprovalGatewayImpl(session),
    ).dispatch(
        principal=principal,
        permission=permission,
        risk_tier=risk,
        action=action,
        business_action=work,
        request_id=request.state.request_id,
    )
    DefaultAuditRecorder(session).record(
        principal=principal,
        entity=entity,
        action=action,
        diff={"result": _jsonable(result)},
        request_id=request.state.request_id,
    )
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (ApiToken, FileObject, Job, Store)):
        return {"id": str(value.id)}
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


__all__ = ["get_principal", "router"]
