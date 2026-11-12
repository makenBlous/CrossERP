"""平台 Listing JSON API。"""

# FastAPI 依赖默认值需要 Depends/Query/Body/Path。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Path, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import ListingCreateRequest, ListingStatusRequest, ListingUpdateRequest
from crosserp.catalog.listing import ListingService
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


def get_permission_service(request: Request) -> PermissionService:
    """从应用容器取得权限服务; 应用未完成装配时显式失败。"""
    return cast(PermissionService, request.app.state.permission_service)


def _service(
    request: Request,
    principal: Principal,
    permission_service: PermissionService,
) -> ListingService:
    return ListingService(
        Session(request.app.state.database_engine),
        principal,
        permission_service,
        request_id=request.state.request_id,
        tool_call_id=request.headers.get("X-Tool-Call-ID"),
    )


@router.get("/catalog/listings")
@api_endpoint(entity="Listing", action="Listing.list", permission="listing:read", risk_tier="none")
def list_listings(
    request: Request,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    service = _service(request, principal, permission_service)
    try:
        with service.session.begin():
            return service.list(page=page, page_size=page_size, q=q, sort=sort)
    finally:
        service.session.close()


@router.get("/catalog/listings/{id}")
@api_endpoint(entity="Listing", action="Listing.get", permission="listing:read", risk_tier="none")
def get_listing(
    request: Request,
    id: UUID = Path(...),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    service = _service(request, principal, permission_service)
    try:
        with service.session.begin():
            return service.get(id)
    finally:
        service.session.close()


@router.post("/catalog/listings", status_code=201)
@api_endpoint(
    entity="Listing", action="Listing.create", permission="listing:create", risk_tier="medium"
)
def create_listing(
    request: Request,
    body: ListingCreateRequest = Body(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    service = _service(request, principal, permission_service)
    try:
        with service.session.begin():
            return service.create(body, idempotency_key)
    finally:
        service.session.close()


@router.patch("/catalog/listings/{id}")
@api_endpoint(
    entity="Listing", action="Listing.update", permission="listing:write", risk_tier="medium"
)
def update_listing(
    request: Request,
    id: UUID = Path(...),
    body: ListingUpdateRequest = Body(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    service = _service(request, principal, permission_service)
    try:
        with service.session.begin():
            return service.update(id, body, idempotency_key)
    finally:
        service.session.close()


@router.post("/catalog/listings/status")
@api_endpoint(
    entity="Listing", action="Listing.status", permission="listing:write", risk_tier="medium"
)
def change_listing_status(
    request: Request,
    body: ListingStatusRequest = Body(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    service = _service(request, principal, permission_service)
    try:
        with service.session.begin():
            return service.status(body, idempotency_key)
    finally:
        service.session.close()


__all__ = ["router"]
