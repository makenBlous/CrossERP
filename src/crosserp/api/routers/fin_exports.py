"""导出产物 JSON API。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _require
from crosserp.api.schemas import PageParams
from crosserp.fin.exports import list_exports

router = APIRouter(tags=["平台结算对账与资金"])


class ExportPageParams(PageParams):
    """OpenAPI PageSize 的默认值是 20。"""

    page_size: int = Field(default=20, alias="pageSize", ge=1, le=200)


@router.get("/finance/exports")
@api_endpoint(
    entity="ExportPackage",
    action="ExportPackage.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_exports(
    request: Request,
    params: Annotated[ExportPageParams, Depends()],
    q: str | None = Query(default=None),
    sort: str = Query(default="-createdAt"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "report:read", entity="ExportPackage")
        return list_exports(
            session,
            principal=principal,
            permission_service=request.app.state.permission_service,
            page=params.page,
            page_size=params.page_size,
            q=q,
            sort=sort,
        )
    finally:
        session.close()


__all__ = ["router"]
