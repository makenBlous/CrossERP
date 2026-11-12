"""科目表与汇率 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _write_guard
from crosserp.finance.reference import (
    FxRateCreatePayload,
    create_fx_rate,
    list_accounts,
    list_fx_rates,
)
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["平台结算对账与资金"])


def get_database_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)


@router.get("/finance/accounts")
@api_endpoint(
    entity="Account",
    action="Account.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_accounts(
    permission_service: PermissionService = Depends(get_permission_service),
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    return list_accounts(
        principal=principal,
        permission_service=permission_service,
        page=page,
        page_size=page_size,
        q=q,
        sort=sort,
    )


@router.get("/finance/fx-rates")
@api_endpoint(
    entity="FxRate",
    action="FxRate.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_fx_rates(
    database_engine: Engine = Depends(get_database_engine),
    permission_service: PermissionService = Depends(get_permission_service),
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    with Session(database_engine) as session:
        return list_fx_rates(
            session,
            principal=principal,
            permission_service=permission_service,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
        )


@router.post("/finance/fx-rates")
@api_endpoint(
    entity="FxRate",
    action="FxRate.create",
    permission="integration:write",
    risk_tier="high",
    idempotency="dispatcher",
)
def post_finance_fx_rates(
    request: Request,
    body: FxRateCreatePayload,
    database_engine: Engine = Depends(get_database_engine),
    permission_service: PermissionService = Depends(get_permission_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    with Session(database_engine) as session, session.begin():
        return create_fx_rate(
            session,
            principal=principal,
            permission_service=permission_service,
            payload=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


__all__ = ["router"]
