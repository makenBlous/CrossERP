"""CrossERP JSON API 基础设施。"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import ModuleType
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from crosserp.api.errors import APIError, ErrorCode, error_payload
from crosserp.api.idempotency import IdempotencyKey
from crosserp.api.metadata import API_METADATA_KEY


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每个请求提供可追踪的 requestId, 并回写响应头。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())
        request.state.request_id = request_id[:64]
        try:
            response = await call_next(request)
        except APIError:
            raise
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """在所有 JSON 写请求前后统一处理 24 小时幂等键。"""

    def __init__(self, app: Any, *, engine: Any) -> None:
        super().__init__(app)
        self.engine = engine

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST":
            return await call_next(request)
        key = request.headers.get("Idempotency-Key")
        if not key:
            return await call_next(request)
        if len(key) > 255:
            request_id = getattr(request.state, "request_id", "")
            return JSONResponse(
                error_payload(
                    ErrorCode.VALIDATION_FAILED,
                    "Idempotency-Key 过长",
                    request_id,
                ),
                status_code=422,
            )
        body = await request.body()
        request_hash = sha256(body).hexdigest()
        now = datetime.now(UTC)
        request_id = getattr(request.state, "request_id", "")
        with Session(self.engine) as session:
            row = session.scalar(
                select(IdempotencyKey).where(
                    IdempotencyKey.key == key,
                    IdempotencyKey.expires_at > now,
                )
            )
            if row is not None:
                if row.request_hash != request_hash:
                    return JSONResponse(
                        error_payload(
                            ErrorCode.IDEMPOTENCY_CONFLICT,
                            "同一 Idempotency-Key 对应了不同请求体",
                            request_id,
                        ),
                        status_code=409,
                    )
                response = _replay_response(row, request_id)
                return response

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        original_receive = request._receive
        request._receive = receive
        try:
            response = await call_next(request)
        finally:
            request._receive = original_receive
        chunks: list[bytes] = []
        async for chunk in cast(Any, response).body_iterator:
            chunks.append(chunk)
        response_body = b"".join(chunks)
        if 200 <= response.status_code < 400:
            with Session(self.engine) as session, session.begin():
                existing = session.scalar(select(IdempotencyKey).where(IdempotencyKey.key == key))
                if existing is None:
                    session.add(
                        IdempotencyKey(
                            key=key,
                            request_hash=request_hash,
                            status_code=response.status_code,
                            response_body=response_body.decode("utf-8", errors="replace"),
                            response_headers={
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() not in {"content-length", "x-request-id"}
                            },
                            created_at=now,
                            expires_at=now + timedelta(hours=24),
                        )
                    )
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(content=response_body, status_code=response.status_code, headers=headers)


def _replay_response(row: IdempotencyKey, request_id: str) -> Response:
    headers = dict(row.response_headers or {})
    headers["X-Request-ID"] = request_id
    return Response(
        content=row.response_body.encode("utf-8"),
        status_code=row.status_code,
        media_type="application/json",
        headers=headers,
    )


def _router_modules() -> Iterable[ModuleType]:
    from crosserp.api import routers

    for info in pkgutil.iter_modules(routers.__path__, routers.__name__ + "."):
        module = importlib.import_module(info.name)
        if hasattr(module, "router"):
            yield module


def register_routers(app: FastAPI) -> None:
    """自动发现 routers 子包中的 router; 新增模块无需修改公共注册表。"""
    for module in _router_modules():
        for route in module.router.routes:
            endpoint = getattr(route, "endpoint", None)
            metadata = getattr(endpoint, API_METADATA_KEY, None)
            if metadata is not None:
                cast(Any, route).openapi_extra = {"x-crosserp": metadata.as_openapi()}
        app.include_router(module.router, prefix="/api/v1")
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        metadata = getattr(endpoint, API_METADATA_KEY, None)
        if metadata is not None:
            cast(Any, route).openapi_extra = {"x-crosserp": metadata.as_openapi()}
        # FastAPI 0.162 stores included routers lazily.  Give the placeholder a
        # path so existing route introspection code can safely inspect app.routes.
        if not hasattr(route, "path") and hasattr(route, "original_router"):
            cast(Any, route).path = "/api/v1"


def install_api(app: FastAPI, engine: Any) -> None:
    """把 API 中间件、异常处理器和自动路由安装到现有 FastAPI 应用。"""
    app.state.database_engine = engine
    app.state.audit_exports = {}
    app.add_middleware(IdempotencyMiddleware, engine=engine)
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            error_payload(exc.code, exc.message, request.state.request_id, exc.details),
            status_code=exc.status_code,
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            error_payload(
                ErrorCode.VALIDATION_FAILED,
                "请求参数校验失败",
                request.state.request_id,
                {"errors": exc.errors()},
            ),
            status_code=422,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            error_payload(
                ErrorCode.VALIDATION_FAILED,
                "请求参数校验失败",
                request.state.request_id,
                {"errors": exc.errors()},
            ),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            error_payload(
                ErrorCode.INTERNAL_ERROR,
                "服务器内部错误",
                request.state.request_id,
            ),
            status_code=500,
        )

    register_routers(app)


__all__ = ["install_api", "register_routers"]
