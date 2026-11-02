"""Money 加减与金额解析的性质测试。"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from crosserp.core.money import Money, money_sum, parse_amount

amounts = st.decimals(
    min_value=-(10**12),
    max_value=10**12,
    places=4,
    allow_nan=False,
    allow_infinity=False,
)


def _group(whole: str, sep: str) -> str:
    parts: list[str] = []
    rest = whole
    while rest:
        parts.append(rest[-3:])
        rest = rest[:-3]
    return sep.join(reversed(parts))


def format_us(value: Decimal) -> str:
    """测试用。把 Decimal 格式化成 US 金额文本。"""
    sign = "-" if value < 0 else ""
    text = format(abs(value), "f")
    if "." in text:
        whole, frac = text.split(".", 1)
        body = _group(whole, ",") + "." + frac
    else:
        body = _group(text, ",")
    return sign + body


def format_eu(value: Decimal) -> str:
    """测试用。把 Decimal 格式化成 EU 金额文本。"""
    us = format_us(value)
    return us.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


@given(a=amounts, b=amounts)
def test_add_sub_roundtrip(a: Decimal, b: Decimal) -> None:
    left = Money(a, "USD")
    right = Money(b, "USD")
    assert (left + right - right).amount == a


@given(a=amounts, b=amounts)
def test_addition_commutative(a: Decimal, b: Decimal) -> None:
    assert (Money(a, "USD") + Money(b, "USD")).amount == (Money(b, "USD") + Money(a, "USD")).amount


@given(a=amounts, b=amounts, c=amounts)
def test_addition_associative(a: Decimal, b: Decimal, c: Decimal) -> None:
    left = (Money(a, "EUR") + Money(b, "EUR")) + Money(c, "EUR")
    right = Money(a, "EUR") + (Money(b, "EUR") + Money(c, "EUR"))
    assert left.amount == right.amount


@given(values=st.lists(amounts, max_size=20))
def test_sum_matches_sequential_add(values: list[Decimal]) -> None:
    items = [Money(value, "EUR") for value in values]
    sequential = Money.zero("EUR")
    for item in items:
        sequential += item
    assert money_sum(items, "EUR") == sequential
    assert sum(items, Money.zero("EUR")) == sequential


@given(value=amounts)
def test_parse_us_roundtrip(value: Decimal) -> None:
    assert parse_amount(format_us(value), "us") == value


@given(value=amounts)
def test_parse_eu_roundtrip(value: Decimal) -> None:
    assert parse_amount(format_eu(value), "eu") == value
