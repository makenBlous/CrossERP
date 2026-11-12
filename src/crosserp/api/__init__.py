"""CrossERP JSON API 基础设施。"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from types import ModuleType
from typing import Any, cast

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from crosserp.api.errors import APIError, ErrorCode, error_payload
from crosserp.api.idempotency import (
    ROUTE_INDEX,
    WRITE_METHODS,
    IdempotencyRecorder,
    IdempotencyReplay,
    bind_dispatcher_scope,
    classify_route,
    replay_authorized_write,
)
from crosserp.api.metadata import ENDPOINT_METADATA
from crosserp.iam.service import IAMService
from crosserp.platform.file_storage import FileStorage
from crosserp.platform.permissions import DefaultPermissionService


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
            if not isinstance(route, APIRoute):
                continue
            metadata = ENDPOINT_METADATA.get(route.endpoint)
            methods = set(route.methods or ())
            if metadata is not None:
                route.openapi_extra = {"x-crosserp": metadata.as_openapi()}
            if methods & WRITE_METHODS and metadata is None:
                raise RuntimeError(f"写接口缺少 api_endpoint 元数据: {route.path}")
            classify_route(
                route.endpoint,
                methods=methods,
                template="/api/v1" + route.path,
            )
            registered = ROUTE_INDEX.get(route.endpoint)
            if registered is None or registered.owner == "none":
                continue
            if registered.owner == "dispatcher":
                route.dependencies.append(Depends(bind_dispatcher_scope))
            elif registered.owner == "http":
                route.dependencies.append(Depends(replay_authorized_write))
            else:
                raise RuntimeError(f"写接口幂等归属无效: {route.path}")
        app.include_router(module.router, prefix="/api/v1")
    for route in app.routes:
        # FastAPI 0.162 stores included routers lazily.  Give the placeholder a
        # path so existing route introspection code can safely inspect app.routes.
        if not hasattr(route, "path") and hasattr(route, "original_router"):
            cast(Any, route).path = "/api/v1"


def install_api(app: FastAPI, engine: Any, *, file_storage: FileStorage) -> None:
    """把 API 中间件、异常处理器和自动路由安装到现有 FastAPI 应用。"""
    app.state.database_engine = engine
    app.state.file_storage = file_storage
    iam_service = IAMService(engine)
    app.state.iam_service = iam_service
    app.state.permission_service = DefaultPermissionService(iam_service)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(IdempotencyRecorder, engine=engine)

    @app.exception_handler(IdempotencyReplay)
    async def handle_idempotency_replay(_request: Request, exc: IdempotencyReplay) -> Response:
        return exc.response

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
                ErrorCode.VALIDATION_ERROR,
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
                ErrorCode.VALIDATION_ERROR,
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
