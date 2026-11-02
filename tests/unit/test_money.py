"""Money 与 parse_amount 单元测试。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from crosserp.core.errors import (
    AmountParseError,
    CrossErpError,
    CurrencyMismatchError,
    PrecisionError,
)
from crosserp.core.money import EU_MARKETPLACES, Money, locale_for, money_sum, parse_amount


def test_error_types() -> None:
    assert issubclass(CurrencyMismatchError, CrossErpError)
    assert issubclass(AmountParseError, CrossErpError)
    assert issubclass(PrecisionError, CrossErpError)


def test_construct_and_reject_float() -> None:
    money = Money(Decimal("1.25"), "USD")
    assert money.amount == Decimal("1.25")
    assert money.currency == "USD"
    with pytest.raises(TypeError, match="float"):
        Money(1.25, "USD")  # type: ignore[arg-type]


def test_construct_rejects_non_decimal_and_bad_currency() -> None:
    with pytest.raises(TypeError):
        Money(1, "USD")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Money(Decimal("NaN"), "USD")
    with pytest.raises(ValueError):
        Money(Decimal("1"), "usd")
    with pytest.raises(ValueError):
        Money(Decimal("1"), "US")
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USDD")
    with pytest.raises(TypeError):
        Money(Decimal("1"), None)  # type: ignore[arg-type]


def test_frozen() -> None:
    money = Money(Decimal("1"), "USD")
    with pytest.raises(AttributeError):
        money.amount = Decimal("2")  # type: ignore[misc]


def test_add_sub_neg_and_currency_mismatch() -> None:
    usd = Money(Decimal("10.00"), "USD")
    other = Money(Decimal("2.50"), "USD")
    assert usd + other == Money(Decimal("12.50"), "USD")
    assert usd - other == Money(Decimal("7.50"), "USD")
    assert -usd == Money(Decimal("-10.00"), "USD")
    assert usd != Money(Decimal("10.00"), "EUR")
    eur = Money(Decimal("1"), "EUR")
    with pytest.raises(CurrencyMismatchError) as added:
        _ = usd + eur
    assert added.value.left == "USD"
    assert added.value.right == "EUR"
    with pytest.raises(CurrencyMismatchError):
        _ = usd - eur


def test_add_does_not_round() -> None:
    total = Money(Decimal("0.0001"), "USD") + Money(Decimal("0.0002"), "USD")
    assert total.amount == Decimal("0.0003")


def test_mul_int_and_decimal() -> None:
    price = Money(Decimal("1.50"), "USD")
    assert price * 3 == Money(Decimal("4.50"), "USD")
    assert 3 * price == Money(Decimal("4.50"), "USD")
    assert price * Decimal("0.5") == Money(Decimal("0.75"), "USD")
    assert Decimal("2") * price == Money(Decimal("3.00"), "USD")
    with pytest.raises(TypeError, match="float"):
        _ = price * 1.5  # type: ignore[operator]
    with pytest.raises(TypeError, match="float"):
        _ = 1.5 * price  # type: ignore[operator]


def test_sum_and_zero() -> None:
    items = [Money(Decimal("1.00"), "EUR"), Money(Decimal("2.50"), "EUR")]
    expected = Money(Decimal("3.50"), "EUR")
    assert money_sum(items, "EUR") == expected
    assert sum(items, Money.zero("EUR")) == expected
    assert sum(items) == expected
    assert money_sum([], "EUR") == Money.zero("EUR")
    with pytest.raises(CurrencyMismatchError):
        money_sum([Money(Decimal("1"), "USD")], "EUR")


def test_quantize_display_half_up() -> None:
    # 1.005 在默认银行家舍入下会变成 1.00。这里必须是 1.01。
    assert Money(Decimal("1.005"), "USD").quantize_display() == Decimal("1.01")
    assert Money(Decimal("1.225"), "USD").quantize_display() == Decimal("1.23")
    assert Money(Decimal("1.224"), "USD").quantize_display() == Decimal("1.22")
    assert Money(Decimal("-1.225"), "USD").quantize_display() == Decimal("-1.23")
    assert Money(Decimal("-1.005"), "USD").quantize_display() == Decimal("-1.01")
    assert Money(Decimal("95"), "EUR").quantize_display() == Decimal("95.00")
    original = Money(Decimal("1.225"), "USD")
    assert original.quantize_display() == Decimal("1.23")
    assert original.amount == Decimal("1.225")


def test_parse_us_examples() -> None:
    assert parse_amount("1,234.56", "us") == Decimal("1234.56")
    assert parse_amount("-12.30", "us") == Decimal("-12.30")
    assert parse_amount("1234", "us") == Decimal("1234")
    # 括号负数。会计惯例。任务标为推断。
    assert parse_amount("(12.30)", "us") == Decimal("-12.30")


def test_parse_eu_examples() -> None:
    assert parse_amount("1.234,56", "eu") == Decimal("1234.56")
    assert parse_amount("95,00", "eu") == Decimal("95.00")
    assert parse_amount("-0,50", "eu") == Decimal("-0.50")
    # 括号负数同样按推断处理。避免 EU 文本漏掉会计负数。
    assert parse_amount("(95,00)", "eu") == Decimal("-95.00")


def test_parse_strips_whitespace_and_nbsp() -> None:
    assert parse_amount("  1,234.56  ", "us") == Decimal("1234.56")
    assert parse_amount("\u00a095,00\u00a0", "eu") == Decimal("95.00")
    with pytest.raises(AmountParseError):
        parse_amount("\u00a0\u00a0", "us")


def test_parse_empty_and_invalid_keep_original() -> None:
    with pytest.raises(AmountParseError) as empty:
        parse_amount("", "us")
    assert empty.value.text == ""
    with pytest.raises(AmountParseError) as blank:
        parse_amount("   ", "eu")
    assert blank.value.text == "   "
    raw = "  nope  "
    with pytest.raises(AmountParseError) as bad:
        parse_amount(raw, "us")
    assert bad.value.text == raw
    assert "nope" in str(bad.value)
    with pytest.raises(AmountParseError):
        parse_amount("95,00", "us")
    with pytest.raises(AmountParseError):
        parse_amount("95.00", "eu")
    with pytest.raises(AmountParseError):
        parse_amount("1 234,56", "eu")


def test_locale_for_mapping() -> None:
    assert (
        frozenset({"amazon.de", "amazon.fr", "amazon.it", "amazon.es", "amazon.nl"})
        == EU_MARKETPLACES
    )
    assert locale_for("Amazon.de", "EUR") == "eu"
    assert locale_for("Amazon.fr", "USD") == "eu"
    assert locale_for(" amazon.it ", "GBP") == "eu"
    assert locale_for("Amazon.es", "EUR") == "eu"
    assert locale_for("Amazon.nl", "USD") == "eu"
    assert locale_for("Amazon.com", "EUR") == "eu"
    assert locale_for(None, "EUR") == "eu"
    assert locale_for(None, " eur ") == "eu"
    assert locale_for("Amazon.com", "USD") == "us"
    assert locale_for("Amazon.co.uk", "GBP") == "us"
    # 未列入映射表的站点不猜测。待真实数据验证。
    assert locale_for("Amazon.pl", "PLN") == "us"
    assert locale_for(None, "USD") == "us"
