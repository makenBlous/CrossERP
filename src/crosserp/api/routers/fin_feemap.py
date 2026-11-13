"""确认费用分类 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _write_guard
from crosserp.finance.feemap import FeeMapConfirmBody, confirm_fee_map
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["平台结算对账与资金"])


@router.post("/finance/fee-map/{id}/confirm")
@api_endpoint(
    entity="MappingRule",
    action="MappingRule.confirm",
    permission="integration:write",
    risk_tier="high",
    idempotency="dispatcher",
)
def post_fee_map_confirm(
    request: Request,
    id: UUID,
    body: FeeMapConfirmBody,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    with Session(request.app.state.database_engine) as session, session.begin():
        return confirm_fee_map(
            session,
            id,
            principal=principal,
            permission_service=permission_service,
            body=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


__all__ = ["router"]
