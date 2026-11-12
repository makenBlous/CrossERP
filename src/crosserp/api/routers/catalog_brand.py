"""品牌主数据 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import BrandCreateRequest, BrandStatusRequest, BrandUpdateRequest
from crosserp.catalog.brand import BrandService
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


def get_permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


@router.get("/catalog/brands")
@api_endpoint(entity="Brand", action="Brand.list", permission="brand:read", risk_tier="none")
def list_brands(
    request: Request,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: Literal["name", "-name"] | None = None,
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return BrandService(session, permission_service).list(
            principal=principal, page=page, page_size=page_size, q=q, sort=sort
        )


@router.post("/catalog/brands", status_code=201)
@api_endpoint(entity="Brand", action="Brand.create", permission="brand:create", risk_tier="medium")
def create_brand(
    request: Request,
    body: BrandCreateRequest,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session, session.begin():
        return BrandService(session, permission_service).create(
            principal=principal,
            payload=body,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )


@router.patch("/catalog/brands/{id}")
@api_endpoint(entity="Brand", action="Brand.update", permission="brand:write", risk_tier="medium")
def update_brand(
    request: Request,
    id: str,
    body: BrandUpdateRequest,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session, session.begin():
        return BrandService(session, permission_service).update(
            principal=principal,
            brand_id=id,
            payload=body,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )


@router.post("/catalog/brands/status")
@api_endpoint(entity="Brand", action="Brand.status", permission="brand:write", risk_tier="medium")
def change_brand_status(
    request: Request,
    body: BrandStatusRequest,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session, session.begin():
        service = BrandService(session, permission_service)
        result = service.status(
            principal=principal,
            brand_id=body.ids[0],
            payload=body,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )
        for extra_id in body.ids[1:]:
            service.status(
                principal=principal,
                brand_id=extra_id,
                payload=body,
                idempotency_key=None,
                request_id=request.state.request_id,
                tool_call_id=request.headers.get("X-Tool-Call-ID"),
            )
        return result


__all__ = ["router"]
