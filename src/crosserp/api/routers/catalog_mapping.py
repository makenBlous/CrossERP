"""平台 SKU 映射 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.catalog.mapping import confirm_mapping, create_mapping, mapping_dict, parse_uuid
from crosserp.db.schema import SkuMapping
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.permissions import DefaultPermissionService, PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


def _service(request: Request) -> PermissionService:
    return getattr(request.app.state, "permission_service", DefaultPermissionService())


def _session(request: Request) -> Session:
    return Session(request.app.state.database_engine)


def _require(principal: Principal, service: PermissionService, permission: str) -> None:
    service.require(principal, permission)


def _dispatcher(request: Request, session: Session, service: PermissionService) -> ActionDispatcher:
    return ActionDispatcher(
        session=session,
        permission_service=service,
        approval_gateway=getattr(request.app.state, "approval_gateway", None),
    )


@router.get("/catalog/mappings")
@api_endpoint(
    entity="SkuMapping", action="SkuMapping.list", permission="listing:read", risk_tier="none"
)
def list_mappings(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    service = _service(request)
    _require(principal, service, "listing:read")
    with _session(request) as session:
        statement = select(SkuMapping)
        scope = service.data_scope_filter(principal, "SkuMapping")
        allowed = scope.get("storeIds", scope.get("storeId")) if scope else None
        if allowed is not None:
            values = allowed if isinstance(allowed, (list, tuple, set, frozenset)) else [allowed]
            statement = statement.where(
                SkuMapping.store_id.in_([UUID(str(value)) for value in values])
            )
        if q:
            term = f"%{q}%"
            statement = statement.where(
                or_(SkuMapping.platform_sku.like(term), SkuMapping.internal_sku.like(term))
            )
        count = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        field_name = (sort or "platformSku").lstrip("-")
        field = {
            "platformSku": SkuMapping.platform_sku,
            "internalSku": SkuMapping.internal_sku,
            "createdAt": SkuMapping.created_at,
            "updatedAt": SkuMapping.updated_at,
        }.get(field_name)
        if field is None:
            raise APIError(ErrorCode.VALIDATION_FAILED, "sort 字段不支持")
        ordering = field.desc() if sort and sort.startswith("-") else field.asc()
        rows = list(
            session.scalars(
                statement.order_by(ordering).offset((page - 1) * page_size).limit(page_size)
            )
        )
    return {
        "items": [mapping_dict(row) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": int(count),
    }


@router.post("/catalog/mappings", status_code=201)
@api_endpoint(
    entity="SkuMapping", action="SkuMapping.create", permission="item:write", risk_tier="medium"
)
def post_mapping(
    request: Request,
    response: Response,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    payload = {} if body is None else body
    service = _service(request)
    with _session(request) as session:
        dispatcher = _dispatcher(request, session, service)
        mapping_id = parse_uuid(payload["id"], "id") if payload.get("id") else uuid4()
        result = cast(
            dict[str, Any],
            dispatcher.dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.MEDIUM,
                action="SkuMapping.create",
                entity="SkuMapping",
                entity_id=mapping_id,
                payload=payload,
                idempotency_key=request.headers.get("Idempotency-Key"),
                request_id=getattr(request.state, "request_id", None),
                business_action=lambda: create_mapping(
                    session,
                    principal,
                    {**payload, "id": str(mapping_id)},
                    permission_service=service,
                ),
            ),
        )
    response.status_code = 201
    return result


@router.post("/catalog/mappings/confirm")
@api_endpoint(
    entity="SkuMapping", action="SkuMapping.confirm", permission="item:write", risk_tier="high"
)
def post_mapping_confirm(
    request: Request,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    payload = {} if body is None else body
    mapping_id = parse_uuid(payload.get("id", payload.get("mappingId")), "id")
    expected_version = payload.get("expectedVersion")
    if expected_version is not None and not isinstance(expected_version, int):
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是整数")
    service = _service(request)
    with _session(request) as session:
        row = session.get(SkuMapping, mapping_id)
        if row is None:
            raise not_found(message="映射不存在")
        dispatcher = _dispatcher(request, session, service)
        return cast(
            dict[str, Any],
            dispatcher.dispatch(
                principal=principal,
                permission="item:write",
                risk_tier=RiskTier.HIGH,
                action="SkuMapping.confirm",
                entity="SkuMapping",
                entity_id=mapping_id,
                expected_version=expected_version,
                payload=payload,
                idempotency_key=request.headers.get("Idempotency-Key"),
                request_id=getattr(request.state, "request_id", None),
                business_action=lambda: confirm_mapping(
                    session,
                    principal,
                    mapping_id,
                    permission_service=service,
                    expected_version=expected_version,
                ),
            ),
        )


__all__ = ["router"]
