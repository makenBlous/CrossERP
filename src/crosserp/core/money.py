"""金额类型与解析。

内存中的金额只用 Decimal。禁止 float。不能用 float 构造或参与运算。
只在展示时用 quantize_display() 做 ROUND_HALF_UP。中间结果不舍入。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from crosserp.core.errors import AmountParseError, CurrencyMismatchError

Locale = Literal["us", "eu"]

# 待真实数据验证。Amazon 欧洲站点 marketplace-name 的实际取值。
# 只收录任务列出的站点。其他站点拿到真实文件前不添加。
EU_MARKETPLACES: frozenset[str] = frozenset(
    {
        "amazon.de",
        "amazon.fr",
        "amazon.it",
        "amazon.es",
        "amazon.nl",
    }
)

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
# 千分位必须成组。不允许把另一种地区格式误认进来。
_US_RE = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$")
_EU_RE = re.compile(r"^(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?$")
_DISPLAY_QUANTUM = Decimal("0.01")


def _reject_float(value: object, action: str) -> None:
    if isinstance(value, float):
        raise TypeError(f"禁止 float。{action}")


@dataclass(frozen=True)
class Money:
    """一种币种下的金额。amount 必须是有限 Decimal。currency 为 3 位大写 ISO 代码。"""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        _reject_float(self.amount, "金额必须用 Decimal。不能传入 float")
        if not isinstance(self.amount, Decimal):
            raise TypeError("金额必须是 Decimal")
        if not self.amount.is_finite():
            raise ValueError("金额必须是有限 Decimal")
        if not isinstance(self.currency, str):
            raise TypeError("币种必须是 str")
        if _CURRENCY_RE.fullmatch(self.currency) is None:
            raise ValueError("币种必须是 3 位大写 ISO 代码")

    @classmethod
    def zero(cls, currency: str) -> Money:
        """该币种的零金额。可作 sum() 的起始值。"""
        return cls(Decimal("0"), currency)

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError("只能与 Money 相加")
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __radd__(self, other: object) -> Money:
        # sum() 的起始值是 0。空序列请用 money_sum 或 Money.zero。
        _reject_float(other, "金额运算不能使用 float")
        if other == 0 and isinstance(other, int) and not isinstance(other, bool):
            return self
        raise TypeError("只能与 Money 相加")

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError("只能与 Money 相减")
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __mul__(self, other: object) -> Money:
        return Money(self.amount * _factor(other), self.currency)

    def __rmul__(self, other: object) -> Money:
        return self.__mul__(other)

    def quantize_display(self) -> Decimal:
        """展示用。ROUND_HALF_UP 到 2 位。不要用于中间计算。"""
        return self.amount.quantize(_DISPLAY_QUANTUM, rounding=ROUND_HALF_UP)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)


def money_sum(items: Iterable[Money], currency: str) -> Money:
    """同一币种相加。空序列返回该币种的零。"""
    total = Money.zero(currency)
    for item in items:
        total += item
    return total


def parse_amount(text: str, locale: Locale) -> Decimal:
    """按 us / eu 小数格式解析金额。

    去掉首尾空白和不换行空格。括号负数如 ``(12.30)`` 按会计惯例视为负数。推断。
    空字符串和无法解析的文本抛 AmountParseError。并保留原文。
    """
    if not isinstance(text, str):
        raise TypeError("金额文本必须是 str")
    if locale not in ("us", "eu"):
        raise ValueError(f"未知金额地区格式 {locale!r}")

    original = text
    # str.strip() 会去掉首尾空白。含不换行空格 U+00A0。
    body = text.strip()
    if body == "":
        raise AmountParseError(original)

    negative = False
    if body.startswith("("):
        if not body.endswith(")") or body.startswith(("(+", "(-")):
            raise AmountParseError(original)
        body = body[1:-1].strip()
        if body == "" or body[0] in "+-()":
            raise AmountParseError(original)
        negative = True
    elif body.endswith(")"):
        raise AmountParseError(original)
    elif body.startswith("+"):
        body = body[1:]
    elif body.startswith("-"):
        negative = True
        body = body[1:]

    if body == "":
        raise AmountParseError(original)

    if locale == "us":
        if _US_RE.fullmatch(body) is None:
            raise AmountParseError(original)
        normalized = body.replace(",", "")
    else:
        if _EU_RE.fullmatch(body) is None:
            raise AmountParseError(original)
        if "," in body:
            whole, frac = body.split(",", 1)
            normalized = whole.replace(".", "") + "." + frac
        else:
            normalized = body.replace(".", "")

    if negative:
        normalized = "-" + normalized
    return Decimal(normalized)


def locale_for(marketplace: str | None, currency: str) -> Locale:
    """按币种和站点选择小数格式。

    EUR 或 marketplace 落在 EU_MARKETPLACES 中时返回 ``eu``。否则返回 ``us``。
    映射表待真实数据验证。
    """
    if not isinstance(currency, str):
        raise TypeError("currency 必须是 str")
    if marketplace is not None and not isinstance(marketplace, str):
        raise TypeError("marketplace 必须是 str 或 None")
    if currency.strip().upper() == "EUR":
        return "eu"
    if marketplace is not None and marketplace.strip().casefold() in EU_MARKETPLACES:
        return "eu"
    return "us"


_MINOR_QUANTUM = Decimal("0.0001")
_MINOR_SCALE = Decimal(10000)


def to_amount_minor(amount: Decimal) -> int:
    """把 Decimal 金额转成万分位整数。

    先按 07 的过账边界用 ROUND_HALF_UP 量化到 4 位再乘 10000。
    量化之后必须是整数。不用 int 截断剩余小数。
    """
    _reject_float(amount, "金额必须用 Decimal。不能传入 float")
    if not isinstance(amount, Decimal):
        raise TypeError("金额必须是 Decimal")
    if not amount.is_finite():
        raise ValueError("金额必须是有限 Decimal")
    quantized = amount.quantize(_MINOR_QUANTUM, rounding=ROUND_HALF_UP)
    scaled = quantized * _MINOR_SCALE
    if scaled != scaled.to_integral_value():
        raise ValueError("万分位转换后不是整数")
    return int(scaled)


def _factor(other: object) -> int | Decimal:
    _reject_float(other, "金额运算不能使用 float")
    if isinstance(other, bool) or not isinstance(other, int | Decimal):
        raise TypeError("数量只能是 int 或 Decimal")
    if isinstance(other, Decimal) and not other.is_finite():
        raise ValueError("乘数必须是有限 Decimal")
    return other
