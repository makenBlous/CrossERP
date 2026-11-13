"""利润报表 JSON 接口。查询只读取已保存的利润快照。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _page
from crosserp.api.schemas import PageParams
from crosserp.core.money import to_amount_minor
from crosserp.db.repo.profit import list_snapshots
from crosserp.db.schema import ProfitSnapshot, Store
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["平台结算对账与资金"])

_PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_SORT_FIELDS = frozenset({"internalSku", "period", "storeName", "revenue", "profit", "status"})
_ENTITY = "ProfitView"
_PERMISSION = "report:read"
_AMOUNT_FIELDS = {
    "revenue": "sku.margin:read",
    "fees": "sku.margin:read",
    "refunds": "sku.margin:read",
    "promotion": "sku.margin:read",
    "ads": "sku.margin:read",
    "profit": "sku.margin:read",
    "profitCny": "sku.margin:read",
    "cogs": "sku.cost:read",
    "freight": "sku.cost:read",
}


class ProfitPageParams(PageParams):
    """利润列表与 OpenAPI PageSize 默认值一致。"""

    page_size: int = Field(default=20, alias="pageSize", ge=1, le=200)


def money_payload(amount: Decimal | None, currency: str) -> dict[str, Any] | None:
    if amount is None:
        return None
    return {"amountMinor": to_amount_minor(amount), "currency": currency}


def _fx(rate: Decimal | None) -> str | None:
    if rate is None:
        return None
    return format(rate, "f")


def _item(row: ProfitSnapshot, store: Store, name: str | None) -> dict[str, Any]:
    currency = row.currency
    return {
        "id": str(row.id),
        "period": row.period,
        "internalSku": row.internal_sku,
        "storeId": str(row.store_id),
        "storeName": store.name,
        "name": name,
        "currency": currency,
        "revenue": money_payload(row.revenue, currency),
        "fees": money_payload(row.fees, currency),
        "refunds": money_payload(row.refunds, currency),
        "promotion": money_payload(row.promotion, currency),
        "cogs": money_payload(row.cogs, currency),
        "freight": money_payload(row.freight, currency),
        "ads": money_payload(row.ads, currency),
        "profit": money_payload(row.profit, currency),
        "profitCny": money_payload(row.profit_cny, "CNY"),
        "fxRate": _fx(row.fx_rate),
        "qtySold": row.qty_sold,
        "qtyRefunded": row.qty_refunded,
        "qtyNet": row.qty_net,
        "status": row.status,
        "adsIncluded": row.ads_included,
        "calcVersion": row.calc_version,
    }


def _period(value: str | None) -> str | None:
    if value is None:
        return None
    if _PERIOD.fullmatch(value) is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "period 必须是 YYYY-MM")
    return value


def _sort(value: str | None) -> str | None:
    if value is None:
        return None
    field = value[1:] if value.startswith("-") else value
    if field not in _SORT_FIELDS:
        raise APIError(ErrorCode.VALIDATION_FAILED, "sort 参数无效")
    return value


def _visible(
    permission_service: PermissionService, principal: Principal, record: dict[str, Any]
) -> dict[str, Any]:
    return permission_service.serialize(principal, record, _AMOUNT_FIELDS)


@router.get("/finance/profit")
@api_endpoint(
    entity="ProfitView",
    action="ProfitView.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def list_profit(
    request: Request,
    params: ProfitPageParams = Depends(),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    store_id: UUID | None = Query(default=None, alias="storeId"),
    period: str | None = Query(default=None),
    sku: str | None = Query(default=None),
) -> dict[str, Any]:
    session = Session(request.app.state.database_engine)
    try:
        permission_service.require(principal, _PERMISSION)
        rows, total = list_snapshots(
            session,
            scope=permission_service.store_scope(principal, _ENTITY),
            store_id=store_id,
            period=_period(period),
            internal_sku=sku,
            q=q,
            sort=_sort(sort),
            offset=(params.page - 1) * params.page_size,
            limit=params.page_size,
        )
        return _page(
            params,
            [
                _visible(permission_service, principal, _item(row, store, name))
                for row, store, name in rows
            ],
            total,
        )
    finally:
        session.close()


@router.get("/finance/profit/sku/{internalSku}")
@api_endpoint(
    entity="ProfitView",
    action="ProfitView.read_sku",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def read_profit_sku(
    request: Request,
    internalSku: str,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
    store_id: UUID | None = Query(default=None, alias="storeId"),
    period: str | None = Query(default=None),
) -> dict[str, Any]:
    session = Session(request.app.state.database_engine)
    try:
        permission_service.require(principal, _PERMISSION)
        rows, _total = list_snapshots(
            session,
            scope=permission_service.store_scope(principal, _ENTITY),
            store_id=store_id,
            period=_period(period),
            internal_sku=internalSku,
            q=None,
            sort="-period",
            offset=0,
            limit=None,
        )
        if not rows:
            raise not_found()
        items = [
            _visible(permission_service, principal, _item(row, store, name))
            for row, store, name in rows
        ]
        return {
            "internalSku": internalSku,
            "period": items[0]["period"],
            "row": items[0],
            "rows": items,
        }
    finally:
        session.close()


__all__ = ["money_payload", "router"]
