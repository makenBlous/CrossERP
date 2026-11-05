"""AI 只读工具。

工具只读取数据库已经保存的确定性结果; 金额转为字符串, 比较差额也由这里
使用 Decimal 计算, 不把算钱工作交给模型。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from crosserp.agent.db import agent_session
from crosserp.agent.rules_search import search_rules_doc as _search_rules_doc
from crosserp.db.schema import (
    Approval,
    Issue,
    OrderLine,
    ProfitSnapshot,
    ReconRun,
    Settlement,
    SettlementLine,
    Store,
    Voucher,
    VoucherLine,
)


class Citation(BaseModel):
    table: str
    id: str
    field: str
    value: str


class ToolResult(BaseModel):
    data: Any
    citations: list[Citation] = Field(default_factory=list)


def get_profit(store: str, period: str) -> ToolResult:
    with agent_session() as session:
        rows = list(
            session.execute(
                select(ProfitSnapshot, Store)
                .join(Store, Store.id == ProfitSnapshot.store_id)
                .where(
                    ProfitSnapshot.period == period,
                    or_(Store.name == store, Store.id == _uuid_or_none(store)),
                )
                .order_by(ProfitSnapshot.internal_sku)
            )
        )
    data = [_snapshot_data(row, store_row) for row, store_row in rows]
    citations = [
        _cite("profit_snapshot", str(row.id), "profit", _text(row.profit)) for row, _ in rows
    ]
    return ToolResult(data=data, citations=citations)


def list_issues(
    status: str | None = None,
    kind: str | None = None,
    store: str | None = None,
    limit: int = 50,
) -> ToolResult:
    _limit(limit)
    with agent_session() as session:
        statement = select(Issue).order_by(Issue.created_at.desc()).limit(limit)
        if status:
            statement = statement.where(Issue.status == status)
        if kind:
            statement = statement.where(Issue.kind == kind)
        rows = list(session.scalars(statement))
    data = [
        {"id": str(row.id), "kind": row.kind, "status": row.status, "detail": row.detail_json}
        for row in rows
    ]
    return ToolResult(
        data=data, citations=[_cite("issue", str(row.id), "status", row.status) for row in rows]
    )


def get_order(order_no: str) -> ToolResult:
    with agent_session() as session:
        rows = list(
            session.scalars(select(OrderLine).where(OrderLine.platform_order_id == order_no))
        )
    data = [
        {
            "id": str(row.id),
            "order_no": row.platform_order_id,
            "sku": row.platform_sku,
            "qty": row.qty,
            "item_price": _text(row.item_price),
        }
        for row in rows
    ]
    return ToolResult(
        data=data,
        citations=[
            _cite("order_line", str(row.id), "item_price", _text(row.item_price)) for row in rows
        ],
    )


def get_settlement(settlement_id: str) -> ToolResult:
    settlement_uuid = UUID(settlement_id)
    with agent_session() as session:
        settlement = session.get(Settlement, settlement_uuid)
        lines = list(
            session.scalars(
                select(SettlementLine).where(SettlementLine.settlement_id == settlement_uuid)
            )
        )
    if settlement is None:
        raise LookupError(f"结算不存在: {settlement_id}")
    data = {
        "id": settlement_id,
        "external_id": settlement.external_id,
        "total": _text(settlement.total),
        "currency": settlement.currency,
        "lines": [
            {"id": str(line.id), "amount": _text(line.amount), "sku": line.sku} for line in lines
        ],
    }
    citations = [_cite("settlement", settlement_id, "total", _text(settlement.total))]
    citations.extend(
        _cite("settlement_line", str(line.id), "amount", _text(line.amount)) for line in lines
    )
    return ToolResult(data=data, citations=citations)


def get_recon_summary(
    run_id: str | None = None, store: str | None = None, period: str | None = None
) -> ToolResult:
    if run_id is None and (store is None or period is None):
        raise ValueError("run_id 或 store+period 必须提供")
    with agent_session() as session:
        if run_id is not None:
            row = session.get(ReconRun, UUID(run_id))
        else:
            row = session.scalar(
                select(ReconRun)
                .join(Store, Store.id == ReconRun.store_id)
                .where(Store.name == store, ReconRun.period == period)
                .order_by(ReconRun.started_at.desc())
            )
    if row is None:
        raise LookupError("对账运行不存在")
    data = {
        "id": str(row.id),
        "period": row.period,
        "status": row.status,
        "groups_total": row.groups_total,
        "groups_matched": row.groups_matched,
        "non_order_lines": row.non_order_lines,
    }
    return ToolResult(
        data=data,
        citations=[_cite("recon_run", str(row.id), "groups_matched", str(row.groups_matched))],
    )


def get_approval_status(target_type: str, target_id: str) -> ToolResult:
    with agent_session() as session:
        rows = list(
            session.scalars(
                select(Approval)
                .where(Approval.target_type == target_type, Approval.target_id == target_id)
                .order_by(Approval.requested_at.desc())
            )
        )
    data = [
        {
            "id": str(row.id),
            "state": row.state,
            "requested_by": row.requested_by,
            "approver": row.approver,
            "comment": row.comment,
        }
        for row in rows
    ]
    return ToolResult(
        data=data, citations=[_cite("approval", str(row.id), "state", row.state) for row in rows]
    )


def get_voucher(voucher_id: str) -> ToolResult:
    with agent_session() as session:
        row = session.get(Voucher, UUID(voucher_id))
        lines = list(
            session.scalars(
                select(VoucherLine)
                .where(VoucherLine.voucher_id == UUID(voucher_id))
                .order_by(VoucherLine.line_no)
            )
        )
    if row is None:
        raise LookupError(f"凭证不存在: {voucher_id}")
    data = {
        "id": voucher_id,
        "state": row.state,
        "period": row.period,
        "total_debit": _text(row.total_debit),
        "total_credit": _text(row.total_credit),
        "lines": [
            {
                "line_no": line.line_no,
                "account_code": line.account_code,
                "debit": _text(line.debit),
                "credit": _text(line.credit),
            }
            for line in lines
        ],
    }
    return ToolResult(
        data=data,
        citations=[
            _cite("voucher", voucher_id, "total_debit", _text(row.total_debit)),
            _cite("voucher", voucher_id, "total_credit", _text(row.total_credit)),
        ],
    )


def compare_profit(store: str, period_a: str, period_b: str) -> ToolResult:
    first = get_profit(store, period_a)
    second = get_profit(store, period_b)
    by_sku_a = {
        str(item["internal_sku"]): Decimal(str(item["profit"] or "0")) for item in first.data
    }
    by_sku_b = {
        str(item["internal_sku"]): Decimal(str(item["profit"] or "0")) for item in second.data
    }
    data = [
        {
            "internal_sku": sku,
            "profit_a": _text(by_sku_a.get(sku, Decimal(0))),
            "profit_b": _text(by_sku_b.get(sku, Decimal(0))),
            "difference": _text(by_sku_b.get(sku, Decimal(0)) - by_sku_a.get(sku, Decimal(0))),
        }
        for sku in sorted(set(by_sku_a) | set(by_sku_b))
    ]
    return ToolResult(data=data, citations=first.citations + second.citations)


def search_rules_doc(query: str, k: int = 5) -> ToolResult:
    hits = _search_rules_doc(query, k)
    data = [
        {
            "text": hit.text,
            "file": hit.file,
            "line_start": hit.line_start,
            "line_end": hit.line_end,
            "score": hit.score,
        }
        for hit in hits
    ]
    return ToolResult(
        data=data,
        citations=[
            _cite("rules_doc", hit.file, f"lines:{hit.line_start}-{hit.line_end}", hit.text)
            for hit in hits
        ],
    )


def _snapshot_data(row: ProfitSnapshot, store: Store) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "store": store.name,
        "period": row.period,
        "internal_sku": row.internal_sku,
        "revenue": _text(row.revenue),
        "fees": _text(row.fees),
        "refunds": _text(row.refunds),
        "profit": _text(row.profit),
        "currency": row.currency,
        "status": row.status,
    }


def _cite(table: str, row_id: str, field: str, value: object) -> Citation:
    return Citation(
        table=table,
        id=row_id,
        field=field,
        value="" if value is None else str(value),
    )


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _limit(value: int) -> None:
    if value < 1 or value > 200:
        raise ValueError("limit 必须在 1 到 200 之间")


def _uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
