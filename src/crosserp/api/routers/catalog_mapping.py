"""平台 SKU 映射 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.catalog.mapping import (
    MappingConfirmInput,
    MappingCreateInput,
    confirm_mapping,
    create_mapping,
    mapping_dict,
)
from crosserp.db.schema import SkuMapping
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.audit import AuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


def get_permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


def get_approval_gateway(request: Request) -> ApprovalGateway:
    return cast(ApprovalGateway, request.app.state.approval_gateway)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.database_engine) as session:
        yield session


def get_audit_recorder(request: Request, session: Session = Depends(get_session)) -> AuditRecorder:
    factory = request.app.state.audit_recorder_factory
    return cast(AuditRecorder, factory(session))


def _dispatcher(
    session: Session,
    service: PermissionService,
    approval_gateway: ApprovalGateway,
    audit_recorder: AuditRecorder,
) -> ActionDispatcher:
    return ActionDispatcher(
        session=session,
        permission_service=service,
        approval_gateway=approval_gateway,
        audit_recorder=audit_recorder,
    )


@router.get("/catalog/mappings")
@api_endpoint(
    entity="SkuMapping", action="SkuMapping.list", permission="listing:read", risk_tier="none"
)
def list_mappings(
    session: Session = Depends(get_session),
    service: PermissionService = Depends(get_permission_service),
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    service.require(principal, "listing:read")
    statement = select(SkuMapping)
    scope = service.data_scope_filter(principal, "SkuMapping")
    allowed = scope.get("storeIds")
    if allowed is not None:
        statement = statement.where(SkuMapping.store_id.in_(allowed))
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
        raise APIError(ErrorCode.VALIDATION_ERROR, "sort 字段不支持")
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
    body: MappingCreateInput,
    session: Session = Depends(get_session),
    service: PermissionService = Depends(get_permission_service),
    approval_gateway: ApprovalGateway = Depends(get_approval_gateway),
    audit_recorder: AuditRecorder = Depends(get_audit_recorder),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    dispatcher = _dispatcher(session, service, approval_gateway, audit_recorder)
    payload = body.model_dump(mode="json", by_alias=True, exclude_none=True)
    result = cast(
        dict[str, Any],
        dispatcher.dispatch(
            principal=principal,
            permission="item:write",
            risk_tier=RiskTier.MEDIUM,
            action="SkuMapping.create",
            entity="SkuMapping",
            entity_id=body.id,
            payload=payload,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            business_action=lambda: create_mapping(
                session,
                principal,
                body,
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
    body: MappingConfirmInput,
    session: Session = Depends(get_session),
    service: PermissionService = Depends(get_permission_service),
    approval_gateway: ApprovalGateway = Depends(get_approval_gateway),
    audit_recorder: AuditRecorder = Depends(get_audit_recorder),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    row = session.get(SkuMapping, body.id)
    if row is None:
        raise not_found(message="映射不存在")
    dispatcher = _dispatcher(session, service, approval_gateway, audit_recorder)
    return cast(
        dict[str, Any],
        dispatcher.dispatch(
            principal=principal,
            permission="item:write",
            risk_tier=RiskTier.HIGH,
            action="SkuMapping.confirm",
            entity="SkuMapping",
            entity_id=body.id,
            expected_version=body.expected_version,
            payload=body.model_dump(mode="json", by_alias=True, exclude_none=True),
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_id=request.state.request_id,
            business_action=lambda: confirm_mapping(
                session,
                principal,
                body.id,
                permission_service=service,
                expected_version=body.expected_version,
            ),
        ),
    )


__all__ = ["router"]
