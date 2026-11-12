"""结算与打款只读 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _page, _principal_db
from crosserp.api.schemas import PageParams
from crosserp.core.money import to_amount_minor
from crosserp.db.repo.settlements import (
    get_settlement_row,
    list_settlement_fees,
    list_settlement_lines,
    query_settlements,
)
from crosserp.db.schema import Fee, Settlement, SettlementLine
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal

router = APIRouter(tags=["平台结算对账与资金"])

_SORT_FIELDS = (
    "periodStart",
    "periodEnd",
    "depositDate",
    "externalId",
    "platform",
    "netPayout",
)
# 目录没有 settlement.amount:read。结算金额按已有敏感金额权限点裁剪。
_AMOUNT_FIELDS = {
    "netPayout": "sku.cost:read",
    "amount": "sku.cost:read",
    "total": "sku.cost:read",
}


class SettlementPageParams(PageParams):
    """结算列表的 OpenAPI 默认 pageSize 为 20。"""

    page_size: int = Field(default=20, alias="pageSize", ge=1, le=200)


def _money(amount: Decimal, currency: str) -> dict[str, int | str]:
    return {"amountMinor": to_amount_minor(amount), "currency": currency}


def _visible(
    permission_service: PermissionService, principal: Principal, record: dict[str, Any]
) -> dict[str, Any]:
    return permission_service.serialize(principal, record, _AMOUNT_FIELDS)


def _sort(sort: str | None) -> tuple[str, bool]:
    value = "-periodEnd" if sort is None else sort
    descending = value.startswith("-")
    field = value[1:] if descending else value
    if field not in _SORT_FIELDS:
        raise APIError(
            ErrorCode.VALIDATION_FAILED,
            "sort 只支持 periodStart、periodEnd、depositDate、externalId、platform、netPayout",
        )
    return field, descending


def _header(row: Settlement, store_name: str) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "storeId": str(row.store_id),
        "storeName": store_name,
        "platform": row.platform,
        "externalId": row.external_id,
        "periodStart": row.period_start.isoformat(),
        "periodEnd": row.period_end.isoformat(),
        "depositDate": None if row.deposit_date is None else row.deposit_date.isoformat(),
        "currency": row.currency,
        "netPayout": _money(row.total, row.currency),
        "sourceBatchId": str(row.source_batch_id),
    }


def _line(line: SettlementLine, currency: str, fee_category: str | None) -> dict[str, Any]:
    return {
        "id": str(line.id),
        "transactionType": line.transaction_type,
        "orderId": line.order_id,
        "orderItemCode": line.order_item_code,
        "sku": line.sku,
        "qty": line.qty,
        "amountType": line.amount_type,
        "amountDescription": line.amount_description,
        "amount": _money(line.amount, currency),
        "postedAt": None if line.posted_at is None else line.posted_at.isoformat(),
        "rawRowId": line.raw_row_id,
        "feeCategory": fee_category,
    }


def _summary(lines: list[SettlementLine], fees: list[Fee], currency: str) -> dict[str, Any]:
    grouped: dict[str, tuple[int, Decimal]] = {}
    for fee in fees:
        if fee.fee_category in grouped:
            count, amount = grouped[fee.fee_category]
        else:
            count, amount = 0, Decimal(0)
        grouped[fee.fee_category] = (count + 1, amount + fee.amount)
    line_total = sum((line.amount for line in lines), Decimal(0))
    return {
        "lineCount": len(lines),
        "total": _money(line_total, currency),
        "byFeeCategory": [
            {
                "feeCategory": category,
                "lineCount": count,
                "amount": _money(amount, currency),
            }
            for category, (count, amount) in sorted(grouped.items())
        ],
    }


@router.get("/finance/settlements")
@api_endpoint(
    entity="Settlement",
    action="Settlement.list",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_settlements(
    request: Request,
    params: SettlementPageParams = Depends(),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        permission_service.require(principal, "report:read")
        field, descending = _sort(sort)
        scope = permission_service.store_scope(principal, "Settlement")
        rows, total = query_settlements(
            session,
            scope=scope,
            q=q,
            sort_field=field,
            descending=descending,
            page=params.page,
            page_size=params.page_size,
        )
        return _page(
            params,
            [
                _visible(permission_service, principal, _header(row, store_name))
                for row, store_name in rows
            ],
            total,
        )
    finally:
        session.close()


@router.get("/finance/settlements/{id}")
@api_endpoint(
    entity="Settlement",
    action="Settlement.get",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_settlement(
    request: Request,
    id: UUID,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        permission_service.require(principal, "report:read")
        scope = permission_service.store_scope(principal, "Settlement")
        found = get_settlement_row(session, id, scope)
        if found is None:
            raise not_found()
        row, store_name = found
        lines = list_settlement_lines(session, row.id)
        fees = list_settlement_fees(session, row.id)
        fee_by_line = {fee.settlement_line_id: fee.fee_category for fee in fees}
        payload = _visible(permission_service, principal, _header(row, store_name))
        payload["lines"] = [
            _visible(
                permission_service,
                principal,
                _line(
                    line,
                    row.currency,
                    fee_by_line.get(line.id),
                ),
            )
            for line in lines
        ]
        summary = _summary(lines, fees, row.currency)
        summary["byFeeCategory"] = [
            _visible(permission_service, principal, item) for item in summary["byFeeCategory"]
        ]
        payload["lineSummary"] = _visible(permission_service, principal, summary)
        payload["provenance"] = {
            "batchId": str(row.source_batch_id),
            "rawRecordIds": [line.raw_row_id for line in lines if line.raw_row_id is not None],
        }
        return payload
    finally:
        session.close()


__all__ = ["router"]
