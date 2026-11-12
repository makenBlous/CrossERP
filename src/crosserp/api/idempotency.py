"""HTTP 层幂等: 只在身份和权限之后回放, 并按调用身份隔离.

走 ActionDispatcher 的写接口不在这里回放. 那些接口由执行器在权限, 数据范围
和版本阶段之后处理. 判断依据是启动时根据 api_endpoint 建立的注册表.
"""

# FastAPI 依赖声明需要在参数默认值调用 Depends.
# ruff: noqa: B008

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from hashlib import sha256
from typing import Any, Literal

from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import ENDPOINT_METADATA
from crosserp.db.schema import IdempotencyKey
from crosserp.platform.idempotency import (
    HttpScope,
    bind_http_scope,
    caller_scope,
    require_key_length,
    reset_http_scope,
    scope_hash,
)
from crosserp.platform.principal import Principal, get_principal

Owner = Literal["dispatcher", "http", "none"]
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class RegisteredIdempotency:
    owner: Owner
    permission: str
    template: str


ROUTE_INDEX: dict[Callable[..., Any], RegisteredIdempotency] = {}


class IdempotencyReplay(Exception):
    """已通过身份和权限校验后的回放响应。"""

    def __init__(self, response: Response) -> None:
        super().__init__("idempotency replay")
        self.response = response


def classify_route(
    endpoint: Callable[..., Any],
    *,
    methods: set[str],
    template: str,
) -> None:
    metadata = ENDPOINT_METADATA.get(endpoint)
    if metadata is None or not methods & WRITE_METHODS:
        return
    ROUTE_INDEX[endpoint] = RegisteredIdempotency(
        metadata.idempotency, metadata.permission, template
    )


async def bind_dispatcher_scope(request: Request) -> AsyncIterator[None]:
    """执行器写接口只绑定路由模板, 不在这里回放."""
    registered = _registered(request)
    token = bind_http_scope(HttpScope(request.method, registered.template))
    try:
        yield
    finally:
        reset_http_scope(token)


async def replay_authorized_write(
    request: Request, principal: Principal = Depends(get_principal)
) -> None:
    """非执行器写接口: 先身份, 再权限, 然后才回放."""
    registered = _registered(request)
    request.app.state.permission_service.require(principal, registered.permission)
    await _replay_or_capture(request, principal, registered)


class IdempotencyRecorder:
    """只记录已经过权限校验的响应, 不在路由匹配前回放."""

    def __init__(self, app: ASGIApp, *, engine: Any) -> None:
        self.app = app
        self.engine = engine

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start: Message | None = None
        chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start
            state = scope["state"]
            if "idempotency_capture" not in state:
                await send(message)
                return
            capture = state["idempotency_capture"]
            if message["type"] == "http.response.start":
                start = message
                return
            if message["type"] != "http.response.body":
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if message.get("more_body", False):
                return
            body = b"".join(chunks)
            status = int(start["status"]) if start is not None else 500
            if 200 <= status < 400:
                _store_capture(self.engine, capture, status, body, start or {})
            if start is not None:
                await send(start)
            await send({"type": "http.response.body", "body": body, "more_body": False})

        await self.app(scope, receive, send_wrapper)


def _registered(request: Request) -> RegisteredIdempotency:
    route = request.scope["route"]
    registered = ROUTE_INDEX.get(route.endpoint)
    if registered is None:
        raise APIError(ErrorCode.INTERNAL_ERROR, "写接口未登记幂等归属")
    return registered


async def _replay_or_capture(
    request: Request, principal: Principal, registered: RegisteredIdempotency
) -> None:
    key = request.headers.get("Idempotency-Key")
    if not key:
        return
    require_key_length(key)
    identity = caller_scope(principal)
    body = await request.body()
    request_hash = _request_hash(request, body)
    digest = scope_hash(
        caller_identity=identity.caller_identity,
        method=request.method,
        route_template=registered.template,
        key=key,
    )
    now = datetime.now(UTC)
    with Session(request.app.state.database_engine) as session:
        row = session.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.idempotency_scope_hash == digest,
                IdempotencyKey.expires_at > now,
            )
        )
    if row is not None:
        if row.request_hash != request_hash:
            raise APIError(ErrorCode.IDEMPOTENCY_CONFLICT, "同一 Idempotency-Key 对应了不同请求体")
        raise IdempotencyReplay(_replay_response(row, request.state.request_id))
    request.state.idempotency_capture = {
        "key": key,
        "caller_identity": identity.caller_identity,
        "represented_user_id": identity.represented_user_id,
        "actor_type": identity.actor_type,
        "actor_key": identity.actor_key,
        "http_method": request.method,
        "route_template": registered.template,
        "idempotency_scope_hash": digest,
        "request_hash": request_hash,
        "now": now,
    }


def _store_capture(
    engine: Any, capture: dict[str, Any], status: int, body: bytes, start: Message
) -> None:
    headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start.get("headers", [])
        if key.decode("latin-1").lower() not in {"content-length", "x-request-id"}
    }
    now = capture["now"]
    with Session(engine) as session, session.begin():
        existing = session.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.idempotency_scope_hash == capture["idempotency_scope_hash"]
            )
        )
        if existing is not None:
            return
        session.add(
            IdempotencyKey(
                key=capture["key"],
                caller_identity=capture["caller_identity"],
                represented_user_id=capture["represented_user_id"],
                actor_type=capture["actor_type"],
                actor_key=capture["actor_key"],
                http_method=capture["http_method"],
                route_template=capture["route_template"],
                idempotency_scope_hash=capture["idempotency_scope_hash"],
                request_hash=capture["request_hash"],
                status_code=status,
                response_body=body.decode("utf-8", errors="replace"),
                response_headers=headers,
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
        )


def _replay_response(row: IdempotencyKey, request_id: str) -> Response:
    headers = dict(row.response_headers or {})
    headers["X-Request-ID"] = request_id
    return Response(
        content=row.response_body.encode("utf-8"),
        status_code=row.status_code,
        media_type="application/json",
        headers=headers,
    )


def _request_hash(request: Request, body: bytes) -> str:
    content_type = request.headers.get("content-type", "")
    if not content_type.casefold().startswith("multipart/form-data"):
        return sha256(body).hexdigest()
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    parts: list[dict[str, str]] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if name is None:
            raise ValueError("multipart 字段缺少 name")
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        data = payload if isinstance(payload, bytes) else b""
        item = {"name": str(name), "filename": filename or ""}
        if filename is None:
            item["value"] = data.decode(part.get_content_charset() or "utf-8")
        else:
            item["sha256"] = sha256(data).hexdigest()
            item["contentType"] = part.get_content_type()
        parts.append(item)
    parts.sort(
        key=lambda item: (
            item["name"],
            item["filename"],
            item.get("value", ""),
            item.get("sha256", ""),
        )
    )
    return sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


__all__ = [
    "ROUTE_INDEX",
    "WRITE_METHODS",
    "IdempotencyKey",
    "IdempotencyRecorder",
    "IdempotencyReplay",
    "bind_dispatcher_scope",
    "classify_route",
    "replay_authorized_write",
]
