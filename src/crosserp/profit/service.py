"""Database orchestration for deterministic profit calculations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.core.enums import IssueKind
from crosserp.db.repo.fx import get_fx_rate
from crosserp.db.repo.profit import get_snapshot, insert_snapshot
from crosserp.db.schema import (
    Fee,
    OrderLine,
    RawRow,
    ReconRun,
    Settlement,
    SettlementLine,
    Sku,
    SkuCost,
    Store,
)
from crosserp.issues.service import open_issue
from crosserp.profit.calc import (
    CostInput,
    LineProfit,
    OrderProfitInput,
    ProfitEntry,
    SkuProfit,
    order_line_profit,
    sku_profit,
)
from crosserp.profit.inputs import CALC_VERSION, inputs_hash


@dataclass(frozen=True)
class PeriodReport:
    store_id: UUID
    period: str
    sku_profits: tuple[SkuProfit, ...]
    unallocated_fees: Decimal
    store_profit: Decimal | None
    store_profit_cny: Decimal | None
    ads_included: bool


def _bounds(period: str) -> tuple[datetime, datetime]:
    year, month = (int(part) for part in period.split("-"))
    start = datetime(year, month, 1, tzinfo=UTC)
    end = (
        datetime(year + 1, 1, 1, tzinfo=UTC)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=UTC)
    )
    return start, end


def _cost_for(session: Session, internal_sku: str, when: datetime) -> SkuCost | None:
    return session.scalar(
        select(SkuCost)
        .where(
            SkuCost.internal_sku == internal_sku,
            SkuCost.valid_from <= when,
            (SkuCost.valid_to.is_(None) | (SkuCost.valid_to > when)),
        )
        .order_by(SkuCost.valid_from.desc())
    )


def _raw_shopify(session: Session, line: SettlementLine) -> tuple[Decimal, Decimal] | None:
    if line.raw_row_id is None:
        return None
    row = session.get(RawRow, line.raw_row_id)
    if row is None or not isinstance(row.payload_json, dict):
        return None
    try:
        amount = Decimal(str(row.payload_json["Amount"]))
        fee = Decimal(str(row.payload_json["Fee"]))
    except (KeyError, ValueError):
        return None
    return amount, fee


def _entry_values(
    session: Session,
    line: SettlementLine,
    fees: list[Fee],
    platform: str,
) -> list[ProfitEntry]:
    if platform == "shopify":
        raw = _raw_shopify(session, line)
        if raw is None:
            return [ProfitEntry(line.id, line.amount, "principal", line.transaction_type)]
        amount, fee = raw
        entries = [ProfitEntry(line.id, amount, "principal", line.transaction_type)]
        if fee != 0:
            entries.append(ProfitEntry(f"{line.id}:fee", -fee, "commission", line.transaction_type))
        return entries
    return [
        ProfitEntry(
            fee.id,
            fee.amount,
            fee.fee_category,
            line.transaction_type,
            line.order_id,
            line.sku,
            line.qty or 0,
        )
        for fee in fees
    ]


def _amounts(
    entries: list[ProfitEntry],
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, int, int]:
    revenue = sum(
        (
            entry.amount
            for entry in entries
            if entry.category in {"principal", "shipping_charge"}
            and entry.transaction_type.casefold() in {"order", "charge"}
        ),
        Decimal(0),
    )
    shipping = sum(
        (entry.amount for entry in entries if entry.category == "shipping_charge"), Decimal(0)
    )
    promotion = sum(
        (entry.amount for entry in entries if entry.category == "promotion"), Decimal(0)
    )
    fees = sum(
        (
            entry.amount
            for entry in entries
            if entry.category in {"commission", "fba", "other", "ads"}
        ),
        Decimal(0),
    )
    refunds = sum(
        (
            entry.amount
            for entry in entries
            if entry.transaction_type.casefold() in {"refund", "chargeback"}
        ),
        Decimal(0),
    )
    sold = sum(
        entry.qty
        for entry in entries
        if entry.transaction_type.casefold() in {"order", "charge"}
        and entry.category == "principal"
    )
    refunded = sum(
        entry.qty
        for entry in entries
        if entry.transaction_type.casefold() in {"refund", "chargeback"}
    )
    return revenue, shipping, promotion, fees, refunds, sold, refunded


def compute_and_save(session: Session, store_id: UUID, period: str) -> PeriodReport:
    """Compute and persist one store/month, retaining prior snapshots."""
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError(f"店铺不存在 {store_id}")
    start, end = _bounds(period)
    settlement_rows = session.execute(
        select(SettlementLine, Settlement)
        .join(Settlement, Settlement.id == SettlementLine.settlement_id)
        .where(
            Settlement.store_id == store_id,
            Settlement.period_end >= start,
            Settlement.period_end < end,
        )
    ).all()
    orders = list(
        session.scalars(
            select(OrderLine)
            .join(Store, Store.id == OrderLine.store_id)
            .where(
                Store.platform == store.platform,
                Store.marketplace == store.marketplace,
                Store.currency == store.currency,
                OrderLine.order_date >= start,
                OrderLine.order_date < end,
            )
        )
    )
    order_by_key: dict[tuple[str, str], list[OrderLine]] = defaultdict(list)
    for order in orders:
        key = (order.platform_order_id.strip().upper(), order.platform_sku.strip().upper())
        order_by_key[key].append(order)
    line_entries: dict[tuple[str, str], list[ProfitEntry]] = defaultdict(list)
    line_ids: list[UUID] = []
    unallocated = Decimal(0)
    for line, settlement in settlement_rows:
        fees = list(session.scalars(select(Fee).where(Fee.settlement_line_id == line.id)))
        entries = _entry_values(session, line, fees, settlement.platform)
        if not line.order_id:
            unallocated += sum((entry.amount for entry in entries), Decimal(0))
            continue
        key = (
            line.order_id.strip().upper(),
            line.sku.strip().upper() if settlement.platform == "amazon" and line.sku else "",
        )
        line_entries[key].extend(entries)
        line_ids.append(line.id)
    line_profits: list[LineProfit] = []
    snapshot_ids: list[object] = [*line_ids]
    latest_recon = session.scalar(
        select(ReconRun)
        .where(
            ReconRun.store_id == store_id,
            ReconRun.period == period,
            ReconRun.status == "done",
        )
        .order_by(ReconRun.finished_at.desc())
    )
    for key, entries in line_entries.items():
        candidates = order_by_key.get(key, [])
        if not candidates and store.platform == "shopify":
            candidates = [
                order for order in orders if order.platform_order_id.strip().upper() == key[0]
            ]
        if not candidates:
            continue
        total_price = sum((order.item_price or Decimal(0) for order in candidates), Decimal(0))
        for order in candidates:
            ratio = (
                Decimal(1)
                if len(candidates) == 1 or total_price == 0
                else (order.item_price or Decimal(0)) / total_price
            )
            allocated = tuple(
                ProfitEntry(
                    entry.record_id,
                    entry.amount * ratio,
                    entry.category,
                    entry.transaction_type,
                    entry.order_id,
                    entry.sku,
                    entry.qty,
                )
                for entry in entries
            )
            revenue, shipping, promotion, fee_total, refunds, sold, refunded = _amounts(
                list(allocated)
            )
            sku = session.scalar(
                select(Sku).where(
                    Sku.platform_sku == order.platform_sku, Sku.store_id == order.store_id
                )
            )
            internal_sku = sku.internal_sku if sku is not None else f"(未映射){order.platform_sku}"
            cost_row = _cost_for(session, internal_sku, order.order_date)
            cost = (
                None
                if cost_row is None
                else CostInput(cost_row.unit_cost, cost_row.freight_per_unit)
            )
            if cost_row is not None:
                snapshot_ids.append(cost_row.id)
            fx: Decimal | None
            if store.currency == "CNY":
                fx = Decimal(1)
            else:
                rate = get_fx_rate(session, period, store.currency, "CNY")
                fx = None if rate is None else rate.rate
                if rate is not None:
                    snapshot_ids.append(rate.id)
            input_row = OrderProfitInput(
                order.id,
                internal_sku,
                store.currency,
                order.order_date,
                sold,
                refunded,
                revenue,
                shipping,
                promotion,
                fee_total,
                refunds,
                allocated,
            )
            line_profit = order_line_profit(list(allocated), input_row, cost, fx)
            line_profits.append(line_profit)
            snapshot_ids.extend([order.id, *(entry.record_id for entry in allocated)])
            if cost is None:
                open_issue(
                    session,
                    IssueKind.COST_MISSING,
                    store_id=store_id,
                    period=period,
                    source_ref=f"profit:{period}:{order.id}:COST_MISSING",
                    detail={"order_id": order.platform_order_id, "sku": order.platform_sku},
                    order_line_id=order.id,
                )
            if fx is None:
                open_issue(
                    session,
                    IssueKind.FX_MISSING,
                    store_id=store_id,
                    period=period,
                    source_ref=f"profit:{period}:{store.currency}:FX_MISSING",
                    detail={"currency": store.currency, "period": period},
                )
    by_sku: dict[str, list[LineProfit]] = defaultdict(list)
    for profit_line in line_profits:
        by_sku[profit_line.internal_sku].append(profit_line)
    sku_results = tuple(sku_profit(lines) for lines in by_sku.values())
    report_hash = inputs_hash(snapshot_ids)
    for result in sku_results:
        if get_snapshot(
            session,
            store_id=store_id,
            period=period,
            internal_sku=result.internal_sku,
            calc_version=CALC_VERSION,
            inputs_hash=report_hash,
        ):
            continue
        insert_snapshot(
            session,
            period=period,
            internal_sku=result.internal_sku,
            store_id=store_id,
            revenue=result.revenue,
            fees=result.fees,
            refunds=result.refunds,
            cogs=result.cogs,
            freight=result.freight,
            ads=None,
            profit=result.profit,
            currency=result.currency,
            calc_version=CALC_VERSION,
            inputs_hash=report_hash,
            qty_sold=result.qty_sold,
            qty_refunded=result.qty_refunded,
            qty_net=result.qty_net,
            promotion=result.promotion,
            fx_rate=result.fx_rate,
            profit_cny=result.profit_cny,
            ads_included=False,
            status=result.status,
            recon_run_id=None if latest_recon is None else latest_recon.id,
        )
    store_profit = (
        None
        if any(result.profit is None for result in sku_results)
        else sum((result.profit for result in sku_results if result.profit is not None), Decimal(0))
    )
    store_profit_cny = (
        None
        if any(result.profit_cny is None for result in sku_results)
        else sum(
            (result.profit_cny for result in sku_results if result.profit_cny is not None),
            Decimal(0),
        )
    )
    return PeriodReport(
        store_id, period, sku_results, unallocated, store_profit, store_profit_cny, False
    )
