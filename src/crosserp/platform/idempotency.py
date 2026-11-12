"""调用身份隔离的幂等范围。人和智能体、不同路由互不可见。"""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import ActionExecution
from crosserp.platform.principal import Principal

# 非 HTTP 入口没有路由模板. HTTP 依赖会在进入端点前写入上下文.
NON_HTTP_METHOD = "CALL"

_http_scope: ContextVar[HttpScope | None] = ContextVar(
    "crosserp_idempotency_http_scope", default=None
)


@dataclass(frozen=True)
class CallerScope:
    """被代表人加实际调用方。智能体的实际调用方是 agent_id。"""

    caller_identity: str
    represented_user_id: str
    actor_type: str
    actor_key: str


@dataclass(frozen=True)
class HttpScope:
    method: str
    route_template: str


def caller_scope(principal: Principal) -> CallerScope:
    """同一键只在这个身份内冲突。AI 代表某人与该人本人不是同一身份。"""
    represented = principal.on_behalf_of or principal.user_id
    if represented is None:
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    if principal.is_agent:
        if not principal.agent_id:
            raise APIError(ErrorCode.AUTH_REQUIRED, "智能体身份缺失")
        actor_type = "agent"
        actor_key = principal.agent_id
    else:
        actor_type = "human"
        actor_key = str(principal.user_id)
    represented_user_id = str(represented)
    return CallerScope(
        caller_identity=f"{represented_user_id}|{actor_type}|{actor_key}",
        represented_user_id=represented_user_id,
        actor_type=actor_type,
        actor_key=actor_key,
    )


def scope_hash(*, caller_identity: str, method: str, route_template: str, key: str) -> str:
    raw = json.dumps(
        [caller_identity, method, route_template, key],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def bind_http_scope(scope: HttpScope) -> Any:
    return _http_scope.set(scope)


def reset_http_scope(token: Any) -> None:
    _http_scope.reset(token)


def current_http_scope(action: str) -> HttpScope:
    bound = _http_scope.get()
    if bound is not None:
        return bound
    return HttpScope(method=NON_HTTP_METHOD, route_template=f"action:{action}")


def require_key_length(key: str) -> None:
    if len(key) > 255:
        raise APIError(ErrorCode.VALIDATION_ERROR, "Idempotency-Key 过长", status_code=422)


def find_action_replay(
    session: Session,
    principal: Principal,
    *,
    key: str | None,
    payload: Any,
    action: str,
) -> Any | None:
    """在同一调用身份、方法、路由模板内查找回放。不同身份看不到这条记录。"""
    if not key:
        return None
    require_key_length(key)
    identity = caller_scope(principal)
    http = current_http_scope(action)
    digest = scope_hash(
        caller_identity=identity.caller_identity,
        method=http.method,
        route_template=http.route_template,
        key=key,
    )
    row = session.scalar(
        select(ActionExecution).where(ActionExecution.idempotency_scope_hash == digest)
    )
    if row is None:
        return None
    if row.request_hash != _payload_hash(payload):
        raise APIError(ErrorCode.IDEMPOTENCY_CONFLICT, "同一 Idempotency-Key 对应了不同请求体")
    return row.result_json


def execution_scope(
    principal: Principal, *, key: str | None, action: str
) -> tuple[CallerScope | None, HttpScope, str | None]:
    http = current_http_scope(action)
    if not key:
        return None, http, None
    require_key_length(key)
    identity = caller_scope(principal)
    return (
        identity,
        http,
        scope_hash(
            caller_identity=identity.caller_identity,
            method=http.method,
            route_template=http.route_template,
            key=key,
        ),
    )


def _payload_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


__all__ = [
    "NON_HTTP_METHOD",
    "CallerScope",
    "HttpScope",
    "bind_http_scope",
    "caller_scope",
    "current_http_scope",
    "execution_scope",
    "find_action_replay",
    "require_key_length",
    "reset_http_scope",
    "scope_hash",
]
