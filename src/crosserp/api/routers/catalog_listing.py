"""平台 Listing JSON API。"""

# FastAPI 依赖默认值需要 Depends/Query/Body/Path。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Path, Query, Request
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.catalog.listing import ListingService
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


def _service(request: Request, principal: Principal) -> ListingService:
    permission_service = getattr(request.app.state, "permission_service", None)
    if permission_service is None:
        permission_service = DefaultPermissionService()
    return ListingService(
        Session(request.app.state.database_engine),
        principal,
        permission_service,
        request_id=getattr(request.state, "request_id", None),
        tool_call_id=request.headers.get("X-Tool-Call-ID"),
    )


@router.get("/catalog/listings")
@api_endpoint(entity="Listing", action="Listing.list", permission="listing:read", risk_tier="none")
def list_listings(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    service = _service(request, principal)
    try:
        with service.session.begin():
            return service.list(page=page, page_size=page_size, q=q, sort=sort)
    finally:
        service.session.close()


@router.get("/catalog/listings/{id}")
@api_endpoint(entity="Listing", action="Listing.get", permission="listing:read", risk_tier="none")
def get_listing(
    request: Request,
    id: str = Path(...),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    service = _service(request, principal)
    try:
        with service.session.begin():
            return service.get(_path_uuid(id))
    finally:
        service.session.close()


@router.post("/catalog/listings", status_code=201)
@api_endpoint(
    entity="Listing", action="Listing.create", permission="listing:create", risk_tier="medium"
)
def create_listing(
    request: Request,
    body: dict[str, Any] | None = Body(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require_idempotency(idempotency_key)
    service = _service(request, principal)
    try:
        with service.session.begin():
            return service.create(body or {}, idempotency_key)
    finally:
        service.session.close()


@router.patch("/catalog/listings/{id}")
@api_endpoint(
    entity="Listing", action="Listing.update", permission="listing:write", risk_tier="medium"
)
def update_listing(
    request: Request,
    id: str = Path(...),
    body: dict[str, Any] | None = Body(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require_idempotency(idempotency_key)
    service = _service(request, principal)
    try:
        with service.session.begin():
            return service.update(_path_uuid(id), body or {}, idempotency_key or "")
    finally:
        service.session.close()


@router.post("/catalog/listings/status")
@api_endpoint(
    entity="Listing", action="Listing.status", permission="listing:write", risk_tier="medium"
)
def change_listing_status(
    request: Request,
    body: dict[str, Any] | None = Body(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require_idempotency(idempotency_key)
    payload = body or {}
    raw_ids = payload.get("ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise APIError(ErrorCode.VALIDATION_FAILED, "ids 必须是非空数组")
    ids = [_uuid(value) for value in raw_ids]
    expected = payload.get("expectedVersion")
    if expected is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须提供")
    if isinstance(expected, bool) or not isinstance(expected, int | dict):
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是整数或按 Listing 映射")
    service = _service(request, principal)
    try:
        with service.session.begin():
            return service.status(ids, payload.get("status"), expected, idempotency_key)
    finally:
        service.session.close()


def _require_idempotency(value: str | None) -> None:
    if not value:
        raise APIError(ErrorCode.VALIDATION_FAILED, "写操作必须提供 Idempotency-Key")


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str):
        raise APIError(ErrorCode.VALIDATION_FAILED, "ids 必须是 UUID 数组")
    try:
        return UUID(value)
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, "ids 必须是 UUID 数组") from exc


def _path_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        from crosserp.api.errors import not_found

        raise not_found(message="Listing 不存在") from None


__all__ = ["router"]
