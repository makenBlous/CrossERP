"""品牌主数据 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
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
    sort: str | None = None,
) -> dict[str, Any]:
    DefaultPermissionService().require(principal, "brand:read")
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).list(page=page, page_size=page_size, q=q, sort=sort)


@router.post("/catalog/brands", status_code=201)
@api_endpoint(entity="Brand", action="Brand.create", permission="brand:create", risk_tier="medium")
def create_brand(
    request: Request,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).create(
            principal=principal,
            payload={} if body is None else body,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )


@router.patch("/catalog/brands/{id}")
@api_endpoint(entity="Brand", action="Brand.update", permission="brand:write", risk_tier="medium")
def update_brand(
    request: Request,
    id: str,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    payload = {} if body is None else body
    with Session(request.app.state.database_engine) as session:
        return BrandService(session).update(
            principal=principal,
            brand_id=id,
            payload=payload,
            expected_version=_expected_version(payload),
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )


@router.post("/catalog/brands/status")
@api_endpoint(entity="Brand", action="Brand.status", permission="brand:write", risk_tier="medium")
def change_brand_status(
    request: Request,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    payload = {} if body is None else body
    raw_ids = payload.get("ids", payload.get("id", payload.get("brandId")))
    brand_id = raw_ids[0] if isinstance(raw_ids, list) and raw_ids else raw_ids
    active_value = payload.get("active")
    status = payload.get("status")
    if status is None and isinstance(active_value, bool):
        status = "active" if active_value else "inactive"
    if not isinstance(brand_id, str) or status not in {"active", "inactive"}:
        raise APIError(ErrorCode.VALIDATION_FAILED, "status 动作需要 id(s) 和 active/inactive")
    with Session(request.app.state.database_engine) as session:
        result = BrandService(session).status(
            principal=principal,
            brand_id=brand_id,
            active=status == "active",
            expected_version=_expected_version(payload),
            payload=payload,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            tool_call_id=request.headers.get("X-Tool-Call-ID"),
        )
        for extra_id in raw_ids[1:] if isinstance(raw_ids, list) else []:
            if not isinstance(extra_id, str):
                raise APIError(ErrorCode.VALIDATION_FAILED, "ids 必须是字符串数组")
            BrandService(session).status(
                principal=principal,
                brand_id=extra_id,
                active=status == "active",
                expected_version=None,
                payload={"id": extra_id, "status": status},
                idempotency_key=None,
                request_id=request.state.request_id,
                tool_call_id=request.headers.get("X-Tool-Call-ID"),
            )
        return result


def _expected_version(payload: dict[str, Any]) -> int | None:
    value = payload.get("expectedVersion")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是非负整数")
    return value


__all__ = ["router"]
