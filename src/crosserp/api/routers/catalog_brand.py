"""品牌主数据 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import BrandCreateRequest, BrandStatusRequest, BrandUpdateRequest
from crosserp.catalog.brand import BrandService
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


@router.get("/catalog/brands")
@api_endpoint(entity="Brand", action="Brand.list", permission="brand:read", risk_tier="none")
def list_brands(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: Literal["name", "-name"] | None = None,
) -> dict[str, Any]:
    DefaultPermissionService().require(principal, "brand:read")
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).list(page=page, page_size=page_size, q=q, sort=sort)


@router.post("/catalog/brands", status_code=201)
@api_endpoint(entity="Brand", action="Brand.create", permission="brand:create", risk_tier="medium")
def create_brand(
    request: Request,
    body: BrandCreateRequest,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).create(
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
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).update(
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
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        result = BrandService(session).status(
            principal=principal,
            brand_id=body.ids[0],
            payload=body,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )
        for extra_id in body.ids[1:]:
            BrandService(session).status(
                principal=principal,
                brand_id=extra_id,
                payload=body,
                idempotency_key=None,
                request_id=request.state.request_id,
                tool_call_id=request.headers.get("X-Tool-Call-ID"),
            )
        return result


__all__ = ["router"]
