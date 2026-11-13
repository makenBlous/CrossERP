"""财务原始行详情。白名单与网页 row_detail 一致。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db
from crosserp.api.schemas import to_camel
from crosserp.core.money import to_amount_minor
from crosserp.db.schema import (
    Approval,
    ImportBatch,
    Issue,
    OrderLine,
    ProfitSnapshot,
    RawRow,
    ReconRun,
    Settlement,
    SettlementLine,
    Store,
    Voucher,
    VoucherLine,
)
from crosserp.iam.scope import StoreScope, apply_store_scope
from crosserp.platform.permissions import PermissionService, get_permission_service

router = APIRouter(tags=["平台结算对账与资金"])

_TABLES = frozenset(
    {
        "profit_snapshot",
        "order_line",
        "settlement_line",
        "raw_row",
        "issue",
        "voucher",
        "voucher_line",
        "approval",
    }
)
_MONEY_COLUMNS = {
    "order_line": frozenset({"item_price"}),
    "settlement_line": frozenset({"amount"}),
    "profit_snapshot": frozenset(
        {
            "revenue",
            "fees",
            "refunds",
            "cogs",
            "freight",
            "ads",
            "profit",
            "promotion",
            "profit_cny",
        }
    ),
    "voucher": frozenset({"total_debit", "total_credit"}),
    "voucher_line": frozenset({"debit", "credit"}),
}
_AMOUNT_FIELDS = {
    "itemPrice": "sku.cost:read",
    "amount": "sku.cost:read",
    "revenue": "sku.cost:read",
    "fees": "sku.cost:read",
    "refunds": "sku.cost:read",
    "cogs": "sku.cost:read",
    "freight": "sku.cost:read",
    "ads": "sku.cost:read",
    "profit": "sku.cost:read",
    "promotion": "sku.cost:read",
    "profitCny": "sku.cost:read",
    "totalDebit": "sku.cost:read",
    "totalCredit": "sku.cost:read",
    "debit": "sku.cost:read",
    "credit": "sku.cost:read",
}


def _uuid_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise not_found() from None


def _raw_id(value: str) -> int:
    if value == "" or not value.isascii() or not value.isdigit():
        raise not_found()
    parsed = int(value)
    if parsed < 1:
        raise not_found()
    return parsed


def _money(amount: Decimal | None, currency: str) -> dict[str, int | str] | None:
    if amount is not None:
        return {"amountMinor": to_amount_minor(amount), "currency": currency}
    return None


def _fx(rate: Decimal | None) -> str | None:
    if rate is not None:
        return format(rate, "f")
    return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    if type(value) is list:
        return [_jsonable(item) for item in value]
    return value


def _one(session: Session, statement: Any) -> Any:
    row = session.scalars(statement).one_or_none()
    if row is None:
        raise not_found()
    return row


def _direct(session: Session, model: Any, row_id: UUID, column: Any, scope: StoreScope) -> Any:
    return _one(
        session,
        apply_store_scope(select(model).where(model.id == row_id), column, scope),
    )


def _require_raw_scope(session: Session, raw_id: int, scope: StoreScope) -> None:
    order_ids = session.scalars(select(OrderLine.id).where(OrderLine.raw_row_id == raw_id)).all()
    visible_orders = session.scalars(
        apply_store_scope(
            select(OrderLine.id).where(OrderLine.raw_row_id == raw_id),
            OrderLine.store_id,
            scope,
        )
    ).all()
    line_ids = session.scalars(
        select(SettlementLine.id).where(SettlementLine.raw_row_id == raw_id)
    ).all()
    visible_lines = session.scalars(
        apply_store_scope(
            select(SettlementLine.id)
            .join(Settlement, Settlement.id == SettlementLine.settlement_id)
            .where(SettlementLine.raw_row_id == raw_id),
            Settlement.store_id,
            scope,
        )
    ).all()
    if len(order_ids) != len(visible_orders) or len(line_ids) != len(visible_lines):
        raise not_found()
    if len(order_ids) == 0 and len(line_ids) == 0:
        raise not_found()


def _require_issue_scope(session: Session, issue: Issue, scope: StoreScope) -> None:
    proofs = 0
    if issue.settlement_line_id is not None:
        proofs += 1
        _one(
            session,
            apply_store_scope(
                select(SettlementLine.id)
                .join(Settlement, Settlement.id == SettlementLine.settlement_id)
                .where(SettlementLine.id == issue.settlement_line_id),
                Settlement.store_id,
                scope,
            ),
        )
    if issue.order_line_id is not None:
        proofs += 1
        _one(
            session,
            apply_store_scope(
                select(OrderLine.id).where(OrderLine.id == issue.order_line_id),
                OrderLine.store_id,
                scope,
            ),
        )
    if issue.recon_run_id is not None:
        proofs += 1
        _one(
            session,
            apply_store_scope(
                select(ReconRun.id).where(ReconRun.id == issue.recon_run_id),
                ReconRun.store_id,
                scope,
            ),
        )
    if proofs == 0:
        raise not_found()


def _require_profit_report_scope(session: Session, target_id: str, scope: StoreScope) -> None:
    store_name, separator, period = target_id.rpartition(":")
    if separator != ":" or store_name == "" or len(period) != 7:
        raise not_found()
    store = session.scalars(select(Store).where(Store.name == store_name)).one_or_none()
    if store is None:
        raise not_found()
    found = session.scalars(
        apply_store_scope(
            select(ProfitSnapshot.id).where(
                ProfitSnapshot.store_id == store.id,
                ProfitSnapshot.period == period,
            ),
            ProfitSnapshot.store_id,
            scope,
        )
    ).first()
    if found is None:
        raise not_found()


def _require_approval_scope(session: Session, row: Approval, scope: StoreScope) -> None:
    if row.target_type == "voucher":
        _direct(session, Voucher, _uuid_id(row.target_id), Voucher.store_id, scope)
        return
    if row.target_type == "profit_report":
        _require_profit_report_scope(session, row.target_id, scope)
        return
    raise not_found()


def _load(session: Session, table: str, row_id: str, scope: StoreScope) -> Any:
    if table == "profit_snapshot":
        return _direct(session, ProfitSnapshot, _uuid_id(row_id), ProfitSnapshot.store_id, scope)
    if table == "order_line":
        return _direct(session, OrderLine, _uuid_id(row_id), OrderLine.store_id, scope)
    if table == "voucher":
        return _direct(session, Voucher, _uuid_id(row_id), Voucher.store_id, scope)
    if table == "settlement_line":
        parsed = _uuid_id(row_id)
        return _one(
            session,
            apply_store_scope(
                select(SettlementLine)
                .join(Settlement, Settlement.id == SettlementLine.settlement_id)
                .where(SettlementLine.id == parsed),
                Settlement.store_id,
                scope,
            ),
        )
    if table == "voucher_line":
        parsed = _uuid_id(row_id)
        return _one(
            session,
            apply_store_scope(
                select(VoucherLine)
                .join(Voucher, Voucher.id == VoucherLine.voucher_id)
                .where(VoucherLine.id == parsed),
                Voucher.store_id,
                scope,
            ),
        )
    if table == "raw_row":
        raw_pk = _raw_id(row_id)
        raw = session.get(RawRow, raw_pk)
        if raw is None:
            raise not_found()
        _require_raw_scope(session, raw_pk, scope)
        return raw
    if table == "issue":
        issue_id = _uuid_id(row_id)
        issue = session.get(Issue, issue_id)
        if issue is None:
            raise not_found()
        _require_issue_scope(session, issue, scope)
        return issue
    if table == "approval":
        approval_id = _uuid_id(row_id)
        approval = session.get(Approval, approval_id)
        if approval is None:
            raise not_found()
        _require_approval_scope(session, approval, scope)
        return approval
    raise not_found()


def _currency(session: Session, table: str, row: Any) -> str:
    if table == "settlement_line":
        settlement = session.get(Settlement, row.settlement_id)
        if settlement is None:
            raise not_found()
        return settlement.currency
    if table == "voucher_line":
        voucher = session.get(Voucher, row.voucher_id)
        if voucher is None:
            raise not_found()
        return voucher.currency
    return cast(str, row.currency)


def _fields(session: Session, table: str, row: Any) -> dict[str, Any]:
    if table in _MONEY_COLUMNS:
        currency: str | None = _currency(session, table, row)
        money_names = _MONEY_COLUMNS[table]
    else:
        currency = None
        money_names = frozenset()
    fields: dict[str, Any] = {}
    for column in row.__table__.columns:
        name = column.name
        value = getattr(row, name)
        key = to_camel(name)
        if name in money_names:
            money_currency = "CNY" if name == "profit_cny" else currency
            if money_currency is None:
                raise not_found()
            fields[key] = _money(value, money_currency)
        elif table == "profit_snapshot" and name == "fx_rate":
            fields[key] = _fx(value)
        else:
            fields[key] = _jsonable(value)
    return fields


def _attach_evidence(session: Session, table: str, row: Any, body: dict[str, Any]) -> None:
    if table == "raw_row":
        batch = session.get(ImportBatch, row.batch_id)
        if batch is None:
            raise not_found()
        body["sourceFile"] = batch.file_name
        body["rowNo"] = row.row_no
        body["payload"] = row.payload_json
        return
    if table == "order_line":
        batch = session.get(ImportBatch, row.source_batch_id)
        if batch is None:
            raise not_found()
        body["sourceFile"] = batch.file_name
        return
    if table == "settlement_line":
        settlement = session.get(Settlement, row.settlement_id)
        if settlement is None:
            raise not_found()
        batch = session.get(ImportBatch, settlement.source_batch_id)
        if batch is None:
            raise not_found()
        body["sourceFile"] = batch.file_name


@router.get("/finance/rows/{table}/{id}")
@api_endpoint(
    entity="RawRecord",
    action="RawRecord.get",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def get_finance_row(
    request: Request,
    table: str,
    id: str,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        permission_service.require(principal, "integration:read")
        if table not in _TABLES:
            raise not_found()
        scope = permission_service.store_scope(principal, "RawRecord")
        row = _load(session, table, id, scope)
        body: dict[str, Any] = {
            "table": table,
            "id": row.id if table == "raw_row" else str(row.id),
            "fields": permission_service.serialize(
                principal, _fields(session, table, row), _AMOUNT_FIELDS
            ),
        }
        _attach_evidence(session, table, row, body)
        return body
    finally:
        session.close()
