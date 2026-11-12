"""组合装 JSON API。"""

# FastAPI 依赖声明使用 Depends 默认值。
# ruff: noqa: B008

from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import CamelModel, PageParams
from crosserp.catalog.bundles import (
    bundle_in_store_scope,
    bundle_payload,
    create_bundle,
    deactivate_bundle,
    get_bundle,
    update_bundle,
)
from crosserp.db.schema import Bundle
from crosserp.iam.scope import AllStores
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


class BundleComponent(CamelModel):
    internal_sku: str = Field(alias="internalSku", min_length=1, max_length=128)
    qty: Decimal = Field(gt=0)


class BundleCreateRequest(CamelModel):
    bundle_sku: str = Field(alias="bundleSku", min_length=1, max_length=128)
    components: list[BundleComponent]


class BundleUpdateRequest(CamelModel):
    expected_version: int = Field(alias="expectedVersion", ge=1)
    bundle_sku: str | None = Field(default=None, alias="bundleSku", min_length=1, max_length=128)
    components: list[BundleComponent] | None = None


class BundleDeactivateRequest(CamelModel):
    ids: list[UUID] = Field(min_length=1)
    expected_version: int = Field(alias="expectedVersion", ge=1)


def _db(request: Request) -> Session:
    return Session(request.app.state.database_engine, expire_on_commit=False)


def get_permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


def _require(principal: Principal, permission: str, service: PermissionService) -> None:
    service.require(principal, permission)


def _write_guard(request: Request, csrf: str | None) -> None:
    if request.cookies.get("crosserp_session"):
        expected = request.cookies.get("crosserp_csrf")
        if not csrf or not expected or not secrets.compare_digest(csrf, expected):
            raise APIError(ErrorCode.CSRF_INVALID, "CSRF 令牌无效", status_code=403)


def _components(payload: list[BundleComponent]) -> list[dict[str, Any]]:
    return [item.model_dump(by_alias=True) for item in payload]


def _page(items: list[dict[str, Any]], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "pageSize": page_size, "total": total}


def _sort_column(sort: str | None) -> tuple[Any, bool]:
    descending = bool(sort and sort.startswith("-"))
    name = sort.lstrip("-") if sort else "createdAt"
    columns = {
        "bundleSku": Bundle.bundle_sku,
        "active": Bundle.active,
        "version": Bundle.version,
        "createdAt": Bundle.created_at,
        "updatedAt": Bundle.updated_at,
    }
    column = columns.get(name)
    if column is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "不支持的排序字段")
    return column, descending


@router.get("/catalog/bundles")
@api_endpoint(
    entity="Bundle",
    action="Bundle.list",
    permission="item:read",
    risk_tier="none",
    idempotency="none",
)
def list_bundles(
    request: Request,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _require(principal, "item:read", permission_service)
    session = _db(request)
    try:
        statement = select(Bundle)
        if q:
            statement = statement.where(Bundle.bundle_sku.contains(q))
        column, descending = _sort_column(sort)
        statement = statement.order_by(column.desc() if descending else column.asc())
        scope = permission_service.store_scope(principal, "Bundle")
        if isinstance(scope, AllStores):
            total = int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
            rows = list(
                session.scalars(
                    statement.offset((params.page - 1) * params.page_size).limit(params.page_size)
                )
            )
        else:
            visible = [
                row
                for row in session.scalars(statement)
                if bundle_in_store_scope(session, row, principal, permission_service)
            ]
            total = len(visible)
            start = (params.page - 1) * params.page_size
            rows = visible[start : start + params.page_size]
        return _page([bundle_payload(row) for row in rows], params.page, params.page_size, total)
    finally:
        session.close()


@router.post("/catalog/bundles", status_code=201)
@api_endpoint(
    entity="Bundle",
    action="Bundle.create",
    permission="item:write",
    risk_tier="medium",
    idempotency="dispatcher",
)
def create_bundle_endpoint(
    request: Request,
    payload: BundleCreateRequest,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _write_guard(request, csrf)
    _require(principal, "item:write", permission_service)
    session = _db(request)
    try:
        with session.begin():
            dispatcher = make_action_dispatcher(session, permission_service)
            bundle_id = uuid4()
            values = payload.model_dump(by_alias=True)

            def work() -> dict[str, Any]:
                row = create_bundle(
                    session,
                    bundle_id=bundle_id,
                    bundle_sku=payload.bundle_sku,
                    components=_components(payload.components),
                    principal=principal,
                )
                return {
                    **bundle_payload(row),
                    "undo": {"action": "Bundle.deactivate", "id": str(row.id)},
                }

            result = dispatcher.dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.MEDIUM,
                action="Bundle.create",
                entity="Bundle",
                entity_id=bundle_id,
                payload=values,
                idempotency_key=idempotency_key,
                request_id=request.state.request_id,
                business_action=work,
            )
            return cast(dict[str, Any], result)
    finally:
        session.close()


@router.patch("/catalog/bundles/{id}")
@api_endpoint(
    entity="Bundle",
    action="Bundle.update",
    permission="item:write",
    risk_tier="medium",
    idempotency="dispatcher",
)
def update_bundle_endpoint(
    request: Request,
    id: UUID,
    payload: BundleUpdateRequest,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _write_guard(request, csrf)
    _require(principal, "item:write", permission_service)
    session = _db(request)
    try:
        with session.begin():
            if payload.bundle_sku is None and payload.components is None:
                raise APIError(ErrorCode.VALIDATION_FAILED, "至少提供一个修改字段")
            row = get_bundle(session, id)
            if not bundle_in_store_scope(session, row, principal, permission_service):
                raise not_found(message="组合装不存在")
            dispatcher = make_action_dispatcher(session, permission_service)

            def work() -> dict[str, Any]:
                before, after = update_bundle(
                    session,
                    row,
                    bundle_sku=payload.bundle_sku,
                    components=(
                        _components(payload.components) if payload.components is not None else None
                    ),
                    principal=principal,
                )
                return {
                    **after,
                    "before": before,
                    "after": after,
                    "undo": {"action": "Bundle.update", "id": str(row.id), "payload": before},
                }

            result = dispatcher.dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.MEDIUM,
                action="Bundle.update",
                entity="Bundle",
                entity_id=id,
                expected_version=payload.expected_version,
                payload=payload.model_dump(by_alias=True),
                idempotency_key=idempotency_key,
                request_id=request.state.request_id,
                business_action=work,
            )
            return cast(dict[str, Any], result)
    finally:
        session.close()


@router.post("/catalog/bundles/deactivate")
@api_endpoint(
    entity="Bundle",
    action="Bundle.deactivate",
    permission="item:delete",
    risk_tier="critical",
    idempotency="dispatcher",
)
def deactivate_bundles(
    request: Request,
    payload: BundleDeactivateRequest,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _write_guard(request, csrf)
    _require(principal, "item:delete", permission_service)
    target_ids = payload.ids
    session = _db(request)
    try:
        with session.begin():
            results: list[dict[str, Any]] = []
            for target_id in target_ids:
                row = get_bundle(session, target_id)
                if not bundle_in_store_scope(session, row, principal, permission_service):
                    raise not_found(message="组合装不存在")
                if not row.active:
                    raise APIError(ErrorCode.ILLEGAL_TRANSITION, "组合装已作废")
                if row.version != payload.expected_version:
                    raise APIError(
                        ErrorCode.CONFLICT_VERSION,
                        "组合装版本冲突",
                        details={
                            "expectedVersion": payload.expected_version,
                            "actualVersion": row.version,
                        },
                    )
                dispatcher = make_action_dispatcher(session, permission_service)

                def work(row: Bundle = row) -> dict[str, Any]:
                    before, after = deactivate_bundle(session, row)
                    return {**after, "before": before, "after": after}

                result = dispatcher.dispatch(
                    principal=principal,
                    permission="item:delete",
                    risk_tier=RiskTier.CRITICAL,
                    action="Bundle.deactivate",
                    entity="Bundle",
                    entity_id=target_id,
                    expected_version=payload.expected_version,
                    payload={"id": str(target_id), "expectedVersion": payload.expected_version},
                    idempotency_key=idempotency_key if len(target_ids) == 1 else None,
                    request_id=request.state.request_id,
                    business_action=work,
                )
                results.append(cast(dict[str, Any], result))
            if len(results) == 1:
                return {**results[0], "status": "deactivated"}
            return {"status": "deactivated", "items": results}
    finally:
        session.close()


__all__ = ["router"]
