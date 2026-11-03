"""Pure Decimal profit calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class ProfitEntry:
    """One settlement amount already classified by the importer."""

    record_id: Any
    amount: Decimal
    category: str
    transaction_type: str
    order_id: str | None = None
    sku: str | None = None
    qty: int = 0


@dataclass(frozen=True)
class OrderProfitInput:
    """Amounts belonging to one order line before cost calculation."""

    order_line_id: Any
    internal_sku: str
    currency: str
    order_date: Any
    qty_sold: int
    qty_refunded: int
    revenue: Decimal
    shipping_charge: Decimal
    promotion: Decimal
    fees: Decimal
    refunds: Decimal
    entries: tuple[ProfitEntry, ...] = ()


@dataclass(frozen=True)
class CostInput:
    unit_cost: Decimal
    freight_per_unit: Decimal


@dataclass(frozen=True)
class LineProfit:
    order_line_id: Any
    internal_sku: str
    currency: str
    qty_sold: int
    qty_refunded: int
    qty_net: int
    revenue: Decimal
    shipping_charge: Decimal
    promotion: Decimal
    fees: Decimal
    refunds: Decimal
    cogs: Decimal | None
    freight: Decimal | None
    profit: Decimal | None
    profit_cny: Decimal | None
    fx_rate: Decimal | None
    status: str
    input_ids: tuple[str, ...]


@dataclass(frozen=True)
class SkuProfit:
    internal_sku: str
    currency: str
    qty_sold: int
    qty_refunded: int
    qty_net: int
    revenue: Decimal
    shipping_charge: Decimal
    promotion: Decimal
    fees: Decimal
    refunds: Decimal
    cogs: Decimal | None
    freight: Decimal | None
    profit: Decimal | None
    profit_cny: Decimal | None
    fx_rate: Decimal | None
    status: str
    input_ids: tuple[str, ...]


def round2(value: Decimal) -> Decimal:
    """Round only at final display/export precision."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def order_line_profit(
    lines: tuple[ProfitEntry, ...] | list[ProfitEntry],
    order_line: OrderProfitInput,
    cost: CostInput | None,
    fx: Decimal | None,
) -> LineProfit:
    """Calculate one order line using exact Decimal arithmetic."""
    qty_net = order_line.qty_sold
    if cost is None:
        cogs = freight = profit = profit_cny = None
        status = "cost_missing"
    else:
        cogs = Decimal(qty_net) * cost.unit_cost
        freight = Decimal(qty_net) * cost.freight_per_unit
        profit = (
            order_line.revenue
            + order_line.shipping_charge
            + order_line.promotion
            + order_line.fees
            + order_line.refunds
            - cogs
            - freight
        )
        if fx is None:
            profit_cny = None
            status = "fx_missing"
        else:
            profit_cny = round2(profit * fx)
            status = "ok"
    return LineProfit(
        order_line_id=order_line.order_line_id,
        internal_sku=order_line.internal_sku,
        currency=order_line.currency,
        qty_sold=order_line.qty_sold,
        qty_refunded=order_line.qty_refunded,
        qty_net=qty_net,
        revenue=order_line.revenue,
        shipping_charge=order_line.shipping_charge,
        promotion=order_line.promotion,
        fees=order_line.fees,
        refunds=order_line.refunds,
        cogs=cogs,
        freight=freight,
        profit=profit,
        profit_cny=profit_cny,
        fx_rate=fx,
        status=status,
        input_ids=tuple(sorted(str(entry.record_id) for entry in lines)),
    )


def sku_profit(line_profits: tuple[LineProfit, ...] | list[LineProfit]) -> SkuProfit:
    """Aggregate lines while preserving a missing-cost/missing-FX status."""
    if not line_profits:
        raise ValueError("至少需要一条订单利润")
    first = line_profits[0]
    sums = {
        name: sum((getattr(line, name) for line in line_profits), Decimal(0))
        for name in ("revenue", "shipping_charge", "promotion", "fees", "refunds")
    }
    cogs = (
        None
        if any(line.cogs is None for line in line_profits)
        else sum((line.cogs for line in line_profits if line.cogs is not None), Decimal(0))
    )
    freight = (
        None
        if any(line.freight is None for line in line_profits)
        else sum((line.freight for line in line_profits if line.freight is not None), Decimal(0))
    )
    profit = (
        None
        if cogs is None or freight is None
        else (
            sums["revenue"]
            + sums["shipping_charge"]
            + sums["promotion"]
            + sums["fees"]
            + sums["refunds"]
            - cogs
            - freight
        )
    )
    fx_values = {line.fx_rate for line in line_profits}
    fx = next(iter(fx_values)) if len(fx_values) == 1 else None
    profit_cny = None if profit is None or fx is None else round2(profit * fx)
    status = "cost_missing" if cogs is None else ("fx_missing" if fx is None else "ok")
    return SkuProfit(
        internal_sku=first.internal_sku,
        currency=first.currency,
        qty_sold=sum(line.qty_sold for line in line_profits),
        qty_refunded=sum(line.qty_refunded for line in line_profits),
        qty_net=sum(line.qty_net for line in line_profits),
        revenue=sums["revenue"],
        shipping_charge=sums["shipping_charge"],
        promotion=sums["promotion"],
        fees=sums["fees"],
        refunds=sums["refunds"],
        cogs=cogs,
        freight=freight,
        profit=profit,
        profit_cny=profit_cny,
        fx_rate=fx,
        status=status,
        input_ids=tuple(sorted({item for line in line_profits for item in line.input_ids})),
    )
