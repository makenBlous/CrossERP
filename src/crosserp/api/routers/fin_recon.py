"""对账运行 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _write_guard
from crosserp.finance.recon import (
    ReconRunCreatePayload,
    create_recon_run,
    get_recon_run,
    list_recon_runs,
)
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["平台结算对账与资金"])


def get_database_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)


def get_permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


@router.get("/finance/recon-runs")
@api_endpoint(entity="ReconRun", action="ReconRun.list", permission="report:read", risk_tier="none")
def get_finance_recon_runs(
    request: Request,
    database_engine: Engine = Depends(get_database_engine),
    permission_service: PermissionService = Depends(get_permission_service),
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    with Session(database_engine) as session:
        return list_recon_runs(
            session,
            principal=principal,
            permission_service=permission_service,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
        )


@router.post("/finance/recon-runs")
@api_endpoint(
    entity="ReconRun",
    action="ReconRun.create",
    permission="integration:write",
    risk_tier="low",
)
def post_finance_recon_runs(
    request: Request,
    body: ReconRunCreatePayload,
    database_engine: Engine = Depends(get_database_engine),
    permission_service: PermissionService = Depends(get_permission_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    with Session(database_engine) as session, session.begin():
        return create_recon_run(
            session,
            principal=principal,
            permission_service=permission_service,
            payload=body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


@router.get("/finance/recon-runs/{id}")
@api_endpoint(entity="ReconRun", action="ReconRun.get", permission="report:read", risk_tier="none")
def get_finance_recon_run(
    request: Request,
    id: UUID,
    database_engine: Engine = Depends(get_database_engine),
    permission_service: PermissionService = Depends(get_permission_service),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    with Session(database_engine) as session:
        return get_recon_run(
            session,
            principal=principal,
            permission_service=permission_service,
            run_id=id,
        )


__all__ = ["router"]
