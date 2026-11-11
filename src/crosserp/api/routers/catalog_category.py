"""类目树 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.catalog.category import (
    create_category,
    list_categories,
    set_category_status,
    update_category,
)
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


@router.get("/catalog/categories")
@api_endpoint(
    entity="Category", action="Category.list", permission="item_group:read", risk_tier="none"
)
def get_categories(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return list_categories(
            session,
            principal=principal,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
        )


@router.post("/catalog/categories", status_code=201)
@api_endpoint(
    entity="Category", action="Category.create", permission="item_group:create", risk_tier="medium"
)
def post_category(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        return create_category(
            session,
            principal=principal,
            payload=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


@router.patch("/catalog/categories/{id}")
@api_endpoint(
    entity="Category", action="Category.update", permission="item_group:write", risk_tier="medium"
)
def patch_category(
    request: Request,
    id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    category_id = _parse_id(id)
    with Session(request.app.state.database_engine) as session:
        return update_category(
            session,
            principal=principal,
            category_id=category_id,
            payload=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


@router.post("/catalog/categories/status")
@api_endpoint(
    entity="Category", action="Category.status", permission="item_group:write", risk_tier="medium"
)
def post_category_status(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    raw_id = body.get("id")
    if not isinstance(raw_id, str):
        raise APIError(ErrorCode.VALIDATION_FAILED, "id 必须是 UUID")
    category_id = _parse_id(raw_id)
    with Session(request.app.state.database_engine) as session:
        return set_category_status(
            session,
            principal=principal,
            category_id=category_id,
            payload=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


def _parse_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise APIError(ErrorCode.NOT_FOUND, "类目不存在", status_code=404) from exc


__all__ = ["router"]
