"""手算锁定的利润公式。"""

from decimal import Decimal

from crosserp.profit.calc import (
    CostInput,
    OrderProfitInput,
    ProfitEntry,
    order_line_profit,
    sku_profit,
)


def test_order_profit_uses_exact_amounts_and_final_rounding() -> None:
    entries = (
        ProfitEntry("principal", Decimal("100.00"), "principal", "order", qty=2),
        ProfitEntry("fee", Decimal("-5.00"), "commission", "order"),
        ProfitEntry("refund", Decimal("-10.00"), "principal", "refund"),
    )
    order = OrderProfitInput(
        "order-1",
        "INT-1",
        "USD",
        None,
        2,
        1,
        Decimal("100.00"),
        Decimal(0),
        Decimal(0),
        Decimal("-5.00"),
        Decimal("-10.00"),
        entries,
    )
    result = order_line_profit(
        entries, order, CostInput(Decimal("20.00"), Decimal("2.00")), Decimal("7.25")
    )
    # 100 - 5 - 10 - (2*20) - (2*2) = 41.00; 41*7.25 = 297.25.
    assert result.profit == Decimal("41.00")
    assert result.profit_cny == Decimal("297.25")
    assert result.qty_net == 2


def test_missing_cost_is_missing_and_never_zero() -> None:
    order = OrderProfitInput(
        "order-2",
        "INT-2",
        "EUR",
        None,
        1,
        0,
        Decimal("9.99"),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )
    result = order_line_profit((), order, None, Decimal("7.80"))
    assert result.status == "cost_missing"
    assert result.cogs is None
    assert result.profit is None


def test_sku_sum_preserves_exact_values() -> None:
    first = order_line_profit(
        (),
        OrderProfitInput(
            "a",
            "INT-1",
            "USD",
            None,
            1,
            0,
            Decimal("10.005"),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
        ),
        CostInput(Decimal("1"), Decimal("0")),
        Decimal("1"),
    )
    second = order_line_profit(
        (),
        OrderProfitInput(
            "b",
            "INT-1",
            "USD",
            None,
            1,
            0,
            Decimal("10.005"),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            Decimal(0),
        ),
        CostInput(Decimal("1"), Decimal("0")),
        Decimal("1"),
    )
    result = sku_profit((first, second))
    assert result.revenue == Decimal("20.010")
    assert result.profit == Decimal("18.010")
    assert result.profit_cny == Decimal("18.01")
