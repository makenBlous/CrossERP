"""确定性的订单与结算行匹配引擎。"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.core.enums import IssueKind
from crosserp.core.errors import ReconInvariantError
from crosserp.db.repo.recon import create_recon_run, finish_recon_run, insert_match
from crosserp.db.schema import (
    Fee,
    Issue,
    OrderLine,
    RawRow,
    ReconRun,
    Settlement,
    SettlementLine,
    Sku,
    Store,
)
from crosserp.issues.service import open_issue
from crosserp.recon.registry import RULES, Matched, Pass, Unmatched, rule_set_version

ORDER_TYPES = frozenset({"order", "charge", "refund", "chargeback"})
REFUND_TYPES = frozenset({"refund", "chargeback"})


@dataclass(frozen=True)
class ReconResult:
    run_id: UUID
    store_id: UUID
    period: str
    groups_total: int
    groups_matched: int
    match_rate: Decimal | None
    unmatched_by_kind: dict[str, int]
    non_order_lines: int


@dataclass(frozen=True)
class _Group:
    key: tuple[str, str]
    lines: tuple[SettlementLine, ...]
    settlement: Settlement


@dataclass(frozen=True)
class _RuleContext:
    """Read-only values prepared once for the ordered rule registry."""

    candidates: tuple[OrderLine, ...]
    sku_values: frozenset[str]
    all_refunds: bool
    settlement_qty: int
    order_qty: int
    actual_amount: Decimal
    expected_amount: Decimal
    has_expected_amount: bool


def _month_bounds(period: str) -> tuple[datetime, datetime, date]:
    try:
        year, month = (int(part) for part in period.split("-"))
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError as exc:
        raise ValueError("period 必须是 YYYY-MM") from exc
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return start, end, date(year, month, calendar.monthrange(year, month)[1])


def _norm(value: str | None) -> str:
    return "" if value is None else value.strip().upper()


def _kind(line: SettlementLine) -> str:
    return line.transaction_type.strip().casefold()


def _is_order_line(line: SettlementLine) -> bool:
    return _kind(line) in ORDER_TYPES and bool(line.order_id)


def _is_refund(line: SettlementLine) -> bool:
    return _kind(line) in REFUND_TYPES


def _group_key(line: SettlementLine, platform: str) -> tuple[str, str]:
    if platform == "amazon":
        return _norm(line.order_id), _norm(line.sku)
    return _norm(line.order_id), ""


def _order_key(order: OrderLine, platform: str) -> tuple[str, str]:
    if platform == "amazon":
        return _norm(order.platform_order_id), _norm(order.platform_sku)
    return _norm(order.platform_order_id), ""


def _as_decimal(value: object) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        try:
            return Decimal(str(value).replace(",", ""))
        except Exception:
            return None
    return None


def _shopify_gross(session: Session, line: SettlementLine) -> Decimal:
    if line.raw_row_id is None:
        return line.amount
    raw = session.get(RawRow, line.raw_row_id)
    if raw is None or not isinstance(raw.payload_json, dict):
        return line.amount
    return _as_decimal(raw.payload_json.get("Amount")) or line.amount


def _principal_amounts(
    session: Session,
    lines: tuple[SettlementLine, ...],
    platform: str,
) -> Decimal:
    if platform == "shopify":
        return sum(
            (_shopify_gross(session, line) for line in lines if _kind(line) == "charge"), Decimal(0)
        )
    ids = [line.id for line in lines]
    fees = session.scalars(select(Fee).where(Fee.settlement_line_id.in_(ids))).all()
    principal_ids = {fee.settlement_line_id for fee in fees if fee.fee_category == "principal"}
    return sum(
        (line.amount for line in lines if line.id in principal_ids and not _is_refund(line)),
        Decimal(0),
    )


def _detail_base(group: _Group) -> dict[str, Any]:
    return {
        "order_id": group.key[0],
        "sku": group.key[1],
        "settlement_id": group.settlement.external_id,
        "settlement_line_ids": [str(line.id) for line in group.lines],
    }


def _open_recon_issue(
    session: Session,
    *,
    kind: IssueKind,
    group: _Group,
    run: ReconRun,
    detail: dict[str, Any],
    order_line_id: UUID | None = None,
) -> None:
    first = group.lines[0]
    detail = {**_detail_base(group), **detail}
    open_issue(
        session,
        kind,
        store_id=run.store_id,
        period=run.period,
        source_ref=f"{run.id}:{first.id}:{kind.value}",
        detail=detail,
        settlement_line_id=first.id,
        order_line_id=order_line_id,
        recon_run_id=run.id,
    )


def _unbalanced_settlements(session: Session) -> set[str]:
    values: set[str] = set()
    for issue in session.scalars(
        select(Issue).where(Issue.kind == IssueKind.SETTLEMENT_UNBALANCED.value)
    ):
        detail = issue.detail_json
        if isinstance(detail, dict) and isinstance(detail.get("settlement_id"), str):
            values.add(detail["settlement_id"])
    return values


def _import_amount_mismatch(session: Session, order_id: str) -> dict[str, Any] | None:
    """读取导入阶段发现的 Shopify 净额异常。"""
    for issue in session.scalars(
        select(Issue).where(
            Issue.kind == IssueKind.AMOUNT_MISMATCH.value,
            Issue.recon_run_id.is_(None),
        )
    ):
        detail = issue.detail_json
        if isinstance(detail, dict) and detail.get("order_id") == order_id:
            return dict(detail)
    return None


def _default_orders(
    session: Session, store: Store, start: datetime, end: datetime, days: int
) -> list[OrderLine]:
    lower = start - timedelta(days=days)
    upper = end + timedelta(days=days)
    return list(
        session.scalars(
            select(OrderLine)
            .join(Store, Store.id == OrderLine.store_id)
            .where(
                Store.platform == store.platform,
                Store.marketplace == store.marketplace,
                Store.currency == store.currency,
                OrderLine.order_date >= lower,
                OrderLine.order_date < upper,
            )
        )
    )


def reconcile(
    session: Session,
    store_id: UUID,
    period: str,
    *,
    as_of: date | None = None,
    grace_days: int = 14,
    order_window_days: int = 60,
) -> ReconResult:
    """运行一次对账并保留旧运行结果。"""
    start, end, default_as_of = _month_bounds(period)
    if as_of is None:
        as_of = default_as_of
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError(f"店铺不存在 {store_id}")
    run = create_recon_run(
        session,
        store_id=store_id,
        period=period,
        as_of=as_of,
        rule_set_version=rule_set_version(),
        started_at=datetime.now(UTC),
    )
    unbalanced = _unbalanced_settlements(session)
    rows = session.execute(
        select(SettlementLine, Settlement)
        .join(Settlement, Settlement.id == SettlementLine.settlement_id)
        .where(
            Settlement.store_id == store_id,
            Settlement.period_end >= start,
            Settlement.period_end < end,
        )
    ).all()
    groups: dict[tuple[str, str], list[SettlementLine]] = defaultdict(list)
    settlements: dict[tuple[str, str], Settlement] = {}
    non_order_lines = 0
    for line, settlement in rows:
        if settlement.external_id in unbalanced:
            continue
        if not _is_order_line(line):
            non_order_lines += 1
            continue
        key = _group_key(line, settlement.platform)
        groups[key].append(line)
        settlements[key] = settlement
    order_rows = _default_orders(session, store, start, end, order_window_days)
    order_index: dict[tuple[str, str], list[OrderLine]] = defaultdict(list)
    for order in order_rows:
        order_index[_order_key(order, store.platform)].append(order)
    sku_values = {
        _norm(item.platform_sku)
        for item in session.scalars(
            select(Sku)
            .join(Store, Store.id == Sku.store_id)
            .where(
                Store.platform == store.platform,
                Store.marketplace == store.marketplace,
                Store.currency == store.currency,
            )
        )
    }
    groups_matched = 0
    unmatched: dict[str, int] = defaultdict(int)
    for key, line_list in groups.items():
        group = _Group(key=key, lines=tuple(line_list), settlement=settlements[key])
        candidates = order_index.get(key, [])
        imported_mismatch = _import_amount_mismatch(session, key[0])
        if imported_mismatch is not None:
            _open_recon_issue(
                session,
                kind=IssueKind.AMOUNT_MISMATCH,
                group=group,
                run=run,
                detail=imported_mismatch,
            )
            unmatched[IssueKind.AMOUNT_MISMATCH.value] += 1
            continue
        settlement_qty = sum(
            (
                line.qty or 0
                for line in group.lines
                if _kind(line) == "order"
                and line.amount_type == "ItemPrice"
                and line.amount_description == "Principal"
            ),
            0,
        )
        expected = sum(
            (order.item_price for order in candidates if order.item_price is not None), Decimal(0)
        )
        context = _RuleContext(
            candidates=tuple(candidates),
            sku_values=frozenset(sku_values),
            all_refunds=all(_is_refund(line) for line in group.lines),
            settlement_qty=settlement_qty,
            order_qty=sum(order.qty for order in candidates),
            actual_amount=_principal_amounts(session, group.lines, store.platform),
            expected_amount=expected,
            has_expected_amount=any(order.item_price is not None for order in candidates),
        )
        decision: Matched | Unmatched | None = None
        for rule in RULES:
            if not rule.applies(group):
                continue
            result = rule.evaluate(context, group)
            if isinstance(result, Pass):
                continue
            if isinstance(result, (Matched, Unmatched)):
                decision = result
                break
        if decision is None:
            raise ReconInvariantError(f"对账组没有规则结果: {group.key}")
        if isinstance(decision, Unmatched):
            if not decision.issues:
                raise ReconInvariantError(f"未匹配组没有原因码: {group.key}")
            first_order_id = context.candidates[0].id if context.candidates else None
            for issue in decision.issues:
                _open_recon_issue(
                    session,
                    kind=issue.kind,
                    group=group,
                    run=run,
                    detail=issue.detail,
                    order_line_id=first_order_id,
                )
                unmatched[issue.kind.value] += 1
            continue
        groups_matched += 1
        first_order = decision.order_lines[0]
        for line in group.lines:
            insert_match(
                session,
                recon_run_id=run.id,
                settlement_line_id=line.id,
                order_line_id=first_order.id,
                rule_id=decision.rule_id,
                diff=decision.diff,
                matched_at=datetime.now(UTC),
            )
    total = len(groups)
    finish_recon_run(
        session,
        run,
        finished_at=datetime.now(UTC),
        groups_total=total,
        groups_matched=groups_matched,
        non_order_lines=non_order_lines,
    )
    rate = None if total == 0 else Decimal(groups_matched) / Decimal(total)
    return ReconResult(
        run_id=run.id,
        store_id=store_id,
        period=period,
        groups_total=total,
        groups_matched=groups_matched,
        match_rate=rate,
        unmatched_by_kind=dict(unmatched),
        non_order_lines=non_order_lines,
    )


def reconcile_all(
    session: Session,
    period: str,
    store_name: str | None = None,
    *,
    as_of: date | None = None,
) -> list[ReconResult]:
    """按店铺运行对账。"""
    statement = select(Store).order_by(Store.platform, Store.name)
    if store_name is not None:
        statement = statement.where(Store.name == store_name)
    return [
        reconcile(session, store.id, period, as_of=as_of) for store in session.scalars(statement)
    ]
