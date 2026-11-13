"""对账异常 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _require, _write_guard
from crosserp.api.schemas import PageParams
from crosserp.issues.actions import (
    DraftVoucherPayload,
    ResolvePayload,
    draft_voucher_from_issue,
    get_recon_issue,
    list_recon_issues,
    resolve_issue,
)
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["平台结算对账与资金"])


class IssuePageParams(PageParams):
    """异常清单分页契约的默认 pageSize 为 20。"""

    page_size: int = Field(default=20, alias="pageSize", ge=1, le=200)


def _engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)


def _permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


def _require_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key:
        raise APIError(ErrorCode.VALIDATION_FAILED, "缺少 Idempotency-Key", status_code=422)
    return idempotency_key


@router.get("/finance/issues")
@api_endpoint(
    entity="ReconIssue",
    action="ReconIssue.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_issues(
    request: Request,
    params: IssuePageParams = Depends(),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require(request, principal, "report:read", entity="ReconIssue")
    with Session(_engine(request)) as session:
        return list_recon_issues(
            session,
            principal=principal,
            permission_service=_permission_service(request),
            page=params.page,
            page_size=params.page_size,
            q=q,
            sort=sort,
        )


@router.get("/finance/issues/{id}")
@api_endpoint(
    entity="ReconIssue",
    action="ReconIssue.get",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_issue(
    request: Request,
    id: UUID,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require(request, principal, "report:read", entity="ReconIssue")
    with Session(_engine(request)) as session:
        return get_recon_issue(
            session,
            principal=principal,
            permission_service=_permission_service(request),
            issue_id=id,
        )


@router.post("/finance/issues/{id}/resolve")
@api_endpoint(
    entity="ReconIssue",
    action="ReconIssue.resolve",
    permission="integration:write",
    risk_tier="medium",
    idempotency="dispatcher",
)
def post_finance_issue_resolve(
    request: Request,
    id: UUID,
    body: ResolvePayload,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    key = _require_idempotency_key(idempotency_key)
    with Session(_engine(request)) as session, session.begin():
        return resolve_issue(
            session,
            principal=principal,
            permission_service=_permission_service(request),
            issue_id=id,
            payload=body,
            idempotency_key=key,
            request_id=request.state.request_id,
        )


@router.post("/finance/issues/{id}/draft-voucher")
@api_endpoint(
    entity="ReconIssue",
    action="ReconIssue.draft_voucher",
    permission="journal_entry:create",
    risk_tier="high",
    idempotency="dispatcher",
)
def post_finance_issue_draft_voucher(
    request: Request,
    id: UUID,
    body: DraftVoucherPayload,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    key = _require_idempotency_key(idempotency_key)
    with Session(_engine(request)) as session, session.begin():
        return draft_voucher_from_issue(
            session,
            principal=principal,
            permission_service=_permission_service(request),
            issue_id=id,
            payload=body,
            idempotency_key=key,
            request_id=request.state.request_id,
        )


__all__ = ["router"]
