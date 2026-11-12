"""SKU 主档 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from crosserp.api.errors import not_found
from crosserp.api.metadata import api_endpoint
from crosserp.catalog.sku import (
    change_status,
    create_sku,
    ensure_store_allowed,
    get_sku,
    list_lookups,
    list_skus,
    update_sku,
)
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import (
    PermissionService,
    get_permission_service,
)
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


class SkuPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    internal_sku: str = Field(alias="internalSku", min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    platform_sku: str = Field(alias="platformSku", min_length=1, max_length=128)
    store_id: UUID | None = Field(default=None, alias="storeId")
    title_en: str | None = Field(default=None, alias="titleEn", max_length=512)
    brand_id: UUID | None = Field(default=None, alias="brandId")
    category_id: UUID | None = Field(default=None, alias="categoryId")
    uom: str | None = Field(default=None, max_length=32)
    weight_kg: str | None = Field(default=None, alias="weightKg")
    hs_code: str | None = Field(default=None, alias="hsCode", max_length=32)
    aliases: list[str] = Field(default_factory=list)
    active: bool = False


class SkuPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    internal_sku: str | None = Field(
        default=None, alias="internalSku", min_length=1, max_length=128
    )
    title: str | None = Field(default=None, min_length=1, max_length=512)
    platform_sku: str | None = Field(default=None, alias="platformSku", max_length=128)
    store_id: UUID | None = Field(default=None, alias="storeId")
    title_en: str | None = Field(default=None, alias="titleEn", max_length=512)
    brand_id: UUID | None = Field(default=None, alias="brandId")
    category_id: UUID | None = Field(default=None, alias="categoryId")
    uom: str | None = Field(default=None, max_length=32)
    weight_kg: str | None = Field(default=None, alias="weightKg")
    hs_code: str | None = Field(default=None, alias="hsCode", max_length=32)
    aliases: list[str] | None = None
    active: bool | None = None
    expected_version: int | None = Field(default=None, alias="expectedVersion", ge=0)


class StatusPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ids: list[UUID] = Field(min_length=1)
    active: bool
    expected_version: int | None = Field(default=None, alias="expectedVersion", ge=0)


def _require(principal: Principal, permission: str, service: PermissionService) -> None:
    service.require(principal, permission)


@router.get("/catalog/skus")
@api_endpoint(entity="Sku", action="Sku.list", permission="item:read", risk_tier="none")
def list_catalog_skus(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: Literal["internalSku", "-internalSku", "title", "-title", "active", "-active"]
    | None = None,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _require(principal, "item:read", permission_service)
    with Session(request.app.state.database_engine) as session, session.begin():
        return list_skus(
            session,
            principal,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
            permission_service=permission_service,
        )


@router.get("/catalog/skus/{id}")
@api_endpoint(entity="Sku", action="Sku.get", permission="item:read", risk_tier="none")
def get_catalog_sku(
    id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _require(principal, "item:read", permission_service)
    try:
        parsed = UUID(id)
    except ValueError as exc:
        raise not_found(message="SKU 不存在") from exc
    with Session(request.app.state.database_engine) as session:
        return get_sku(session, principal, parsed, permission_service=permission_service)


@router.post("/catalog/skus", status_code=201)
@api_endpoint(entity="Sku", action="Sku.create", permission="item:create", risk_tier="medium")
def create_catalog_sku(
    body: SkuPayload,
    request: Request,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    payload = body.model_dump(by_alias=True, exclude_none=True)
    sku_id = uuid4()
    with Session(request.app.state.database_engine) as session, session.begin():
        ensure_store_allowed(principal, body.store_id, permission_service)
        result = make_action_dispatcher(session, permission_service).dispatch(
            principal=principal,
            permission="item:create",
            risk_tier=RiskTier.MEDIUM,
            action="Sku.create",
            entity="Sku",
            entity_id=sku_id,
            payload=payload,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
            business_action=lambda: create_sku(session, payload, sku_id=sku_id)[1],
        )
    return cast(dict[str, Any], result)


@router.patch("/catalog/skus/{id}")
@api_endpoint(entity="Sku", action="Sku.update", permission="item:write", risk_tier="medium")
def update_catalog_sku(
    id: str,
    body: SkuPatch,
    request: Request,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    try:
        parsed = UUID(id)
    except ValueError as exc:
        raise not_found(message="SKU 不存在") from exc
    payload = body.model_dump(by_alias=True, exclude_none=True)
    expected_version = payload.pop("expectedVersion", None)
    with Session(request.app.state.database_engine) as session, session.begin():
        get_sku(session, principal, parsed, permission_service=permission_service)
        return cast(
            dict[str, Any],
            make_action_dispatcher(session, permission_service).dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.MEDIUM,
                action="Sku.update",
                entity="Sku",
                entity_id=parsed,
                payload=payload,
                expected_version=expected_version,
                idempotency_key=idempotency_key,
                request_id=request.state.request_id,
                business_action=lambda: update_sku(session, parsed, payload),
            ),
        )


@router.post("/catalog/skus/status")
@api_endpoint(entity="Sku", action="Sku.status", permission="item:write", risk_tier="medium")
def status_catalog_skus(
    body: StatusPayload,
    request: Request,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for sku_id in body.ids:
        key = f"{idempotency_key}:{sku_id}" if idempotency_key else None
        with Session(request.app.state.database_engine) as session, session.begin():
            get_sku(session, principal, sku_id, permission_service=permission_service)
            result = make_action_dispatcher(session, permission_service).dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.MEDIUM,
                action="Sku.status",
                entity="Sku",
                entity_id=sku_id,
                payload={"id": str(sku_id), "active": body.active},
                expected_version=body.expected_version,
                idempotency_key=key,
                request_id=request.state.request_id,
                business_action=cast(
                    Callable[[], Any],
                    lambda sku_id=sku_id: change_status(session, sku_id, body.active),
                ),
            )
            results.append(result)
    return {"status": "succeeded", "updated": len(results), "items": results}


@router.get("/catalog/lookups")
@api_endpoint(
    entity="CatalogLookup", action="CatalogLookup.list", permission="item:read", risk_tier="none"
)
def get_catalog_lookups(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: Literal["kind", "-kind", "label", "-label", "value", "-value"] | None = None,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _require(principal, "item:read", permission_service)
    with Session(request.app.state.database_engine) as session:
        return list_lookups(
            session,
            principal,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
            permission_service=permission_service,
        )


__all__ = ["router"]
