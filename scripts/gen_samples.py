# 生成的中文说明使用全角标点。不是同形字攻击。
# ruff: noqa: RUF001, RUF002, RUF003
"""固定种子合成样本生成器。

种子 random.Random(20261109)。金额只用 Decimal，禁止 float。
平台取值在 sample_vocab.py，一律「待真实数据验证」。
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import sample_vocab as vocab
from openpyxl import Workbook

from crosserp.core.money import locale_for, parse_amount

_CENTS = Decimal("0.01")
_RATE_QUANTUM = Decimal("0.00000001")
_COMMISSION_RATE = Decimal("15") / Decimal("100")  # 合成佣金比例，不是亚马逊真实费率
_PARTIAL_REFUND = Decimal("10.00")
_UNKNOWN_FEE = Decimal("-1.23")
_UNBALANCED_DELTA = Decimal("1.00")
_SHOPIFY_FEE_PERCENT = Decimal(2)  # 合成手续费，不是 Shopify 真实费率

_SETTLEMENT_US = "SYN-SETTLE-US-20261014"
_SETTLEMENT_DE = "SYN-SETTLE-DE-20261014"
_SETTLEMENT_UNBALANCED = "SYN-SETTLE-US-UNBALANCED"
_PERIOD_START = "2026-10-01"
_PERIOD_END = "2026-10-14"
_DEPOSIT_DATE = "2026-10-16"

_STORE_US = "amazon-us"
_STORE_DE = "amazon-de"
_STORE_SHOPIFY = "shopify-main"

_SKU_CUP = "CUP-US-001"
_SKU_MUG = "MUG-US-002"
_SKU_BAG = "BAG-US-003"
_SKU_BOT = "BOT-DE-001"
_SKU_PAD = "PAD-DE-002"
_SKU_TEE = "SH-TEE-001"
_SKU_GAP = "COST-GAP-US"
_SKU_UNMAPPED = "SYN-UNMAPPED"

_ID_NOT_IN_ERP = "SYN-US-NOT-IN-ERP"
_ID_REFUND_NO_ORDER = "SYN-US-REFUND-NO-ORDER"
_ID_QTY = "SYN-US-QTY"
_ID_AMT = "SYN-US-AMT"
_ID_UNMAPPED = "SYN-US-UNMAPPED"
_ID_NET = "SYN-SH-NET"
_ID_FEE = "SYN-US-FEE"
_ID_REFUND = "SYN-US-REFUND"
_ID_PARTIAL = "SYN-US-PARTIAL"
_ID_CB = "SYN-US-CB"
_ID_COST = "SYN-US-COST"
_ID_FX = "SYN-DE-FX"
_ID_SH_CB = "SYN-SH-CB"
_ID_PENDING = "SYN-SH-PENDING"
_ID_IN_US = "SYN-US-INTRANSIT"
_ID_IN_DE = "SYN-DE-INTRANSIT"
_ID_NORMAL_US = "SYN-US-0001"

# 这些订单号的订单类组算未匹配。Shopify 净额不符也算，以便守住 5% 上限。
_UNMATCHED_ORDER_IDS = frozenset(
    {
        _ID_NOT_IN_ERP,
        _ID_REFUND_NO_ORDER,
        _ID_QTY,
        _ID_AMT,
        _ID_UNMAPPED,
        _ID_NET,
    }
)
_SHOPIFY_FILE1_IDS = frozenset({f"SYN-SH-{index:04d}" for index in range(1, 5)} | {_ID_SH_CB})
_ZIP_DATE = (2026, 11, 9, 0, 0, 0)
_FIXED_STAMP = "2026-11-09T00:00:00Z"

_MATCH_RATE_DEFINITION = (
    "已匹配的订单类结算行组数 / 全部订单类结算行组数。"
    "Amazon 按 (order-id, sku) 分组。"
    "transaction-type 属于 Order/Refund/Chargeback（待真实数据验证）。"
    "Shopify 按 Order 分组，Type 属于 charge/refund/dispute（待真实数据验证）。"
    "未匹配原因码：NOT_IN_ERP、REFUND_WITHOUT_ORDER、QTY_MISMATCH、AMOUNT_MISMATCH、SKU_UNMAPPED。"
    "Shopify Net ≠ Amount − Fee 使用 AMOUNT_MISMATCH，计入未匹配组。"
    "amazon_us_unbalanced.tsv 不进入分母。"
    "非订单类行不进入分母。重复行不另计一组。"
)


@dataclass(frozen=True)
class Sku:
    platform_sku: str
    internal_sku: str
    store: str
    title: str
    currency: str
    fba_fee: Decimal | None
    mapped: bool = True


@dataclass(frozen=True)
class Order:
    order_id: str
    store: str
    platform_sku: str
    qty: int
    order_date: str
    item_price: Decimal
    currency: str
    in_settlement: bool = True
    settlement_qty: int | None = None
    settlement_principal: Decimal | None = None
    fba_override: Decimal | None = None
    extra: str = ""

    @property
    def order_item_id(self) -> str:
        return f"{self.order_id}-1"

    def qty_in_settlement(self) -> int:
        if self.settlement_qty is None:
            return self.qty
        return self.settlement_qty

    def principal_in_settlement(self) -> Decimal:
        if self.settlement_principal is None:
            return self.item_price
        return self.settlement_principal


def _skus() -> dict[str, Sku]:
    rows = (
        Sku(_SKU_CUP, "INT-CUP-500", _STORE_US, "保温杯 🍵 黑色 500ml", "USD", Decimal("3.50")),
        Sku(_SKU_MUG, "INT-MUG-300", _STORE_US, "马克杯 ☕ 白色 300ml", "USD", Decimal("2.80")),
        Sku(_SKU_BAG, "INT-BAG-01", _STORE_US, "收纳袋 👜 灰色", "USD", Decimal("4.20")),
        Sku(_SKU_BOT, "INT-BOT-750", _STORE_DE, "水瓶 💧 透明 750ml", "EUR", Decimal("3.10")),
        Sku(_SKU_PAD, "INT-PAD-A5", _STORE_DE, "笔记本 📒 A5", "EUR", Decimal("1.90")),
        Sku(_SKU_TEE, "INT-TEE-M", _STORE_SHOPIFY, "短袖 👕 白色 M", "USD", None),
        Sku(_SKU_GAP, "INT-COST-GAP", _STORE_US, "缺成本样品 📦", "USD", Decimal("3.00")),
        Sku(_SKU_UNMAPPED, "", _STORE_US, "", "USD", Decimal("3.00"), mapped=False),
    )
    return {row.platform_sku: row for row in rows}


def _fail(message: str) -> None:
    raise SystemExit(message)


def format_amount(amount: Decimal, locale: str) -> str:
    """输出 2 位小数。US 用点，EU 用逗号。不输出千分位。"""
    if isinstance(amount, float) or not isinstance(amount, Decimal):
        _fail("金额必须是 Decimal，禁止 float")
    quantized = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
    negative = quantized < 0
    text = format(abs(quantized), "f")
    if "." not in text:
        text += ".00"
    whole, frac = text.split(".", 1)
    body = f"{whole}.{(frac + '00')[:2]}"
    if locale == "eu":
        body = body.replace(".", ",")
    elif locale != "us":
        _fail(f"未知金额格式 {locale}")
    if negative:
        return f"-{body}"
    return body


def format_rate(rate: Decimal) -> str:
    if isinstance(rate, float) or not isinstance(rate, Decimal):
        _fail("汇率必须是 Decimal，禁止 float")
    quantized = rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
    text = format(quantized, "f")
    if "." not in text:
        text += ".00000000"
    whole, frac = text.split(".", 1)
    return f"{whole}.{(frac + '00000000')[:8]}"


def _commission(principal: Decimal) -> Decimal:
    return (principal.copy_abs() * _COMMISSION_RATE).quantize(_CENTS, rounding=ROUND_HALF_UP)


def _shopify_fee(amount: Decimal) -> Decimal:
    return (amount.copy_abs() * _SHOPIFY_FEE_PERCENT / Decimal(100)).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )


def _blank_amazon() -> dict[str, str]:
    return {column: "" for column in vocab.AMAZON_V2_COLUMNS}


def _amazon_line(
    *,
    settlement_id: str,
    marketplace: str,
    currency: str,
    locale: str,
    transaction_type: str,
    order_id: str,
    sku: str,
    amount_type: str,
    amount_description: str,
    amount: Decimal,
    qty: int | None,
    posted: str,
    item_code: str,
) -> dict[str, str]:
    row = _blank_amazon()
    row["settlement-id"] = settlement_id
    row["settlement-start-date"] = _PERIOD_START
    row["settlement-end-date"] = _PERIOD_END
    row["deposit-date"] = _DEPOSIT_DATE
    row["currency"] = currency
    row["transaction-type"] = transaction_type
    row["order-id"] = order_id
    row["merchant-order-id"] = order_id
    row["marketplace-name"] = marketplace
    row["amount-type"] = amount_type
    row["amount-description"] = amount_description
    row["amount"] = format_amount(amount, locale)
    if transaction_type == vocab.TX_ORDER:
        row["fulfillment-id"] = vocab.FULFILLMENT_AFN
    row["posted-date"] = posted
    row["posted-date-time"] = f"{posted} {vocab.AMAZON_DATETIME_SUFFIX}"
    row["order-item-code"] = item_code
    row["merchant-order-item-id"] = item_code
    row["sku"] = sku
    if qty is not None:
        row["quantity-purchased"] = str(qty)
    return row


def _summary_row(
    settlement_id: str,
    marketplace: str,
    currency: str,
    total: Decimal,
    locale: str,
) -> dict[str, str]:
    # 汇总行只有总额，没有 transaction-type。推断，待真实数据验证。
    row = _blank_amazon()
    row["settlement-id"] = settlement_id
    row["settlement-start-date"] = _PERIOD_START
    row["settlement-end-date"] = _PERIOD_END
    row["deposit-date"] = _DEPOSIT_DATE
    row["total-amount"] = format_amount(total, locale)
    row["currency"] = currency
    row["marketplace-name"] = marketplace
    return row


def _append_sale(lines: list[dict[str, str]], order: Order, skus: dict[str, Sku]) -> None:
    locale = "eu" if order.currency == "EUR" else "us"
    marketplace = vocab.MARKETPLACE_DE if locale == "eu" else vocab.MARKETPLACE_US
    settlement_id = _SETTLEMENT_DE if locale == "eu" else _SETTLEMENT_US
    principal = order.principal_in_settlement()
    qty = order.qty_in_settlement()
    spec = skus[order.platform_sku]
    if spec.fba_fee is None:
        _fail(f"{order.platform_sku} 没有合成 FBA 参考费")
    fba = spec.fba_fee * Decimal(qty)
    if order.fba_override is not None:
        fba = order.fba_override
    commission = _commission(principal)
    item_code = order.order_item_id
    common = {
        "settlement_id": settlement_id,
        "marketplace": marketplace,
        "currency": order.currency,
        "locale": locale,
        "order_id": order.order_id,
        "sku": order.platform_sku,
        "posted": order.order_date,
        "item_code": item_code,
    }
    lines.append(
        _amazon_line(
            **common,
            transaction_type=vocab.TX_ORDER,
            amount_type=vocab.AMOUNT_TYPE_PRICE,
            amount_description=vocab.DESC_PRINCIPAL,
            amount=principal,
            qty=qty,
        )
    )
    lines.append(
        _amazon_line(
            **common,
            transaction_type=vocab.TX_ORDER,
            amount_type=vocab.AMOUNT_TYPE_FEE,
            amount_description=vocab.DESC_COMMISSION,
            amount=-commission,
            qty=qty,
        )
    )
    lines.append(
        _amazon_line(
            **common,
            transaction_type=vocab.TX_ORDER,
            amount_type=vocab.AMOUNT_TYPE_FEE,
            amount_description=vocab.DESC_FBA,
            amount=-fba,
            qty=qty,
        )
    )
    if order.extra == "refund":
        lines.append(
            _amazon_line(
                **common,
                transaction_type=vocab.TX_REFUND,
                amount_type=vocab.AMOUNT_TYPE_PRICE,
                amount_description=vocab.DESC_PRINCIPAL,
                amount=-principal,
                qty=order.qty,
            )
        )
        lines.append(
            _amazon_line(
                **common,
                transaction_type=vocab.TX_REFUND,
                amount_type=vocab.AMOUNT_TYPE_FEE,
                amount_description=vocab.DESC_COMMISSION,
                amount=commission,
                qty=0,
            )
        )
    elif order.extra == "partial_refund":
        lines.append(
            _amazon_line(
                **common,
                transaction_type=vocab.TX_REFUND,
                amount_type=vocab.AMOUNT_TYPE_PRICE,
                amount_description=vocab.DESC_PRINCIPAL,
                amount=-_PARTIAL_REFUND,
                qty=0,
            )
        )
        lines.append(
            _amazon_line(
                **common,
                transaction_type=vocab.TX_REFUND,
                amount_type=vocab.AMOUNT_TYPE_FEE,
                amount_description=vocab.DESC_COMMISSION,
                amount=_commission(_PARTIAL_REFUND),
                qty=0,
            )
        )
    elif order.extra == "chargeback":
        lines.append(
            _amazon_line(
                **common,
                transaction_type=vocab.TX_CHARGEBACK,
                amount_type=vocab.AMOUNT_TYPE_PRICE,
                amount_description=vocab.DESC_PRINCIPAL,
                amount=-principal,
                qty=0,
            )
        )


def _normal_orders(rng: random.Random) -> list[Order]:
    orders: list[Order] = []
    us_skus = (_SKU_CUP, _SKU_MUG, _SKU_BAG)
    for index in range(1, 87):
        day = (index - 1) % 14 + 1
        cents = rng.randint(1000, 8999)
        orders.append(
            Order(
                order_id=f"SYN-US-{index:04d}",
                store=_STORE_US,
                platform_sku=us_skus[(index - 1) % 3],
                qty=rng.randint(1, 3),
                order_date=f"2026-10-{day:02d}",
                item_price=Decimal(cents) / Decimal(100),
                currency="USD",
            )
        )
    de_skus = (_SKU_BOT, _SKU_PAD)
    for index in range(1, 13):
        day = (index - 1) % 14 + 1
        cents = rng.randint(1000, 8999)
        orders.append(
            Order(
                order_id=f"SYN-DE-{index:04d}",
                store=_STORE_DE,
                platform_sku=de_skus[(index - 1) % 2],
                qty=rng.randint(1, 2),
                order_date=f"2026-10-{day:02d}",
                item_price=Decimal(cents) / Decimal(100),
                currency="EUR",
            )
        )
    for index in range(1, 9):
        day = (index - 1) % 14 + 1
        cents = rng.randint(1500, 6000)
        orders.append(
            Order(
                order_id=f"SYN-SH-{index:04d}",
                store=_STORE_SHOPIFY,
                platform_sku=_SKU_TEE,
                qty=rng.randint(1, 2),
                order_date=f"2026-10-{day:02d}",
                item_price=Decimal(cents) / Decimal(100),
                currency="USD",
            )
        )
    return orders


def _special_orders() -> list[Order]:
    return [
        Order(
            _ID_FEE,
            _STORE_US,
            _SKU_CUP,
            1,
            "2026-10-03",
            Decimal("40.00"),
            "USD",
            fba_override=Decimal("5.50"),
        ),
        Order(
            _ID_REFUND,
            _STORE_US,
            _SKU_MUG,
            1,
            "2026-10-04",
            Decimal("50.00"),
            "USD",
            extra="refund",
        ),
        Order(
            _ID_PARTIAL,
            _STORE_US,
            _SKU_BAG,
            2,
            "2026-10-05",
            Decimal("60.00"),
            "USD",
            extra="partial_refund",
        ),
        Order(
            _ID_CB,
            _STORE_US,
            _SKU_CUP,
            1,
            "2026-10-06",
            Decimal("45.00"),
            "USD",
            extra="chargeback",
        ),
        Order(_ID_COST, _STORE_US, _SKU_GAP, 1, "2026-10-06", Decimal("21.00"), "USD"),
        Order(_ID_FX, _STORE_DE, _SKU_BOT, 1, "2026-10-08", Decimal("95.00"), "EUR"),
        Order(
            _ID_SH_CB,
            _STORE_SHOPIFY,
            _SKU_TEE,
            1,
            "2026-10-04",
            Decimal("35.00"),
            "USD",
            extra="chargeback",
        ),
        Order(
            _ID_PENDING,
            _STORE_SHOPIFY,
            _SKU_TEE,
            1,
            "2026-10-18",
            Decimal("16.00"),
            "USD",
            extra="pending",
        ),
        Order(
            _ID_QTY,
            _STORE_US,
            _SKU_MUG,
            3,
            "2026-10-07",
            Decimal("30.00"),
            "USD",
            settlement_qty=1,
        ),
        Order(
            _ID_AMT,
            _STORE_US,
            _SKU_BAG,
            1,
            "2026-10-08",
            Decimal("25.00"),
            "USD",
            settlement_principal=Decimal("22.00"),
        ),
        Order(_ID_UNMAPPED, _STORE_US, _SKU_UNMAPPED, 1, "2026-10-09", Decimal("18.00"), "USD"),
        Order(
            _ID_NET,
            _STORE_SHOPIFY,
            _SKU_TEE,
            1,
            "2026-10-12",
            Decimal("20.00"),
            "USD",
            extra="net_mismatch",
        ),
    ]


def _in_transit_orders() -> list[Order]:
    return [
        Order(
            _ID_IN_US,
            _STORE_US,
            _SKU_CUP,
            1,
            "2026-10-25",
            Decimal("19.00"),
            "USD",
            in_settlement=False,
        ),
        Order(
            _ID_IN_DE,
            _STORE_DE,
            _SKU_PAD,
            1,
            "2026-10-31",
            Decimal("27.00"),
            "EUR",
            in_settlement=False,
        ),
    ]


def _build_orders(rng: random.Random) -> list[Order]:
    orders = [*_normal_orders(rng), *_special_orders(), *_in_transit_orders()]
    orders.append(
        Order(
            "SYN-US-EXTRA",
            _STORE_US,
            _SKU_CUP,
            1,
            "2026-10-14",
            Decimal("12.34"),
            "USD",
        )
    )
    if len(orders) != 121:
        _fail(f"订单行 {len(orders)} != 121")
    ids = [order.order_id for order in orders]
    if len(ids) != len(set(ids)):
        _fail("订单号重复")
    return orders


def _us_details(orders: list[Order], skus: dict[str, Sku]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for order in orders:
        if order.store == _STORE_US and order.in_settlement:
            _append_sale(lines, order, skus)
    _append_sale(
        lines,
        Order(_ID_NOT_IN_ERP, _STORE_US, _SKU_CUP, 1, "2026-10-09", Decimal("15.00"), "USD"),
        skus,
    )
    lines.append(
        _amazon_line(
            settlement_id=_SETTLEMENT_US,
            marketplace=vocab.MARKETPLACE_US,
            currency="USD",
            locale="us",
            transaction_type=vocab.TX_REFUND,
            order_id=_ID_REFUND_NO_ORDER,
            sku=_SKU_CUP,
            amount_type=vocab.AMOUNT_TYPE_PRICE,
            amount_description=vocab.DESC_PRINCIPAL,
            amount=Decimal("-12.00"),
            qty=1,
            posted="2026-10-11",
            item_code=f"{_ID_REFUND_NO_ORDER}-1",
        )
    )
    lines.append(
        _amazon_line(
            settlement_id=_SETTLEMENT_US,
            marketplace=vocab.MARKETPLACE_US,
            currency="USD",
            locale="us",
            transaction_type=vocab.TX_REFUND,
            order_id=_ID_REFUND_NO_ORDER,
            sku=_SKU_CUP,
            amount_type=vocab.AMOUNT_TYPE_FEE,
            amount_description=vocab.DESC_COMMISSION,
            amount=_commission(Decimal("12.00")),
            qty=0,
            posted="2026-10-11",
            item_code=f"{_ID_REFUND_NO_ORDER}-1",
        )
    )
    lines.append(
        _amazon_line(
            settlement_id=_SETTLEMENT_US,
            marketplace=vocab.MARKETPLACE_US,
            currency="USD",
            locale="us",
            transaction_type=vocab.TX_OTHER,
            order_id="",
            sku="",
            amount_type=vocab.AMOUNT_TYPE_FEE,
            amount_description=vocab.DESC_UNKNOWN,
            amount=_UNKNOWN_FEE,
            qty=None,
            posted="2026-10-14",
            item_code="",
        )
    )
    duplicated = False
    for index, row in enumerate(lines):
        if row["order-id"] == _ID_NORMAL_US and row["amount-description"] == vocab.DESC_FBA:
            lines.insert(index + 1, dict(row))
            duplicated = True
            break
    if not duplicated:
        _fail("找不到要复制的 FBA 行")
    return lines


def _de_details(orders: list[Order], skus: dict[str, Sku]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for order in orders:
        if order.store == _STORE_DE and order.in_settlement:
            _append_sale(lines, order, skus)
    return lines


def _unbalanced_details(skus: dict[str, Sku]) -> list[dict[str, str]]:
    order = Order("SYN-US-UNBAL-1", _STORE_US, _SKU_CUP, 1, "2026-10-02", Decimal("10.00"), "USD")
    lines: list[dict[str, str]] = []
    _append_sale(lines, order, skus)
    for row in lines:
        row["settlement-id"] = _SETTLEMENT_UNBALANCED
    return lines


def _shopify_line(
    order: Order,
    *,
    type_: str,
    amount: Decimal,
    fee: Decimal,
    net: Decimal,
    status: str,
    payout_date: str,
    available_on: str,
    txn_date: str | None = None,
) -> dict[str, str]:
    when = txn_date or f"{order.order_date} 10:15:00 -0400"
    return {
        "Transaction Date": when,
        "Type": type_,
        "Order": order.order_id,
        "Card Brand": vocab.SHOPIFY_CARD_BRAND,
        "Card Source": vocab.SHOPIFY_CARD_SOURCE,
        "Payout Status": status,
        "Payout Date": payout_date,
        "Available On": available_on,
        "Amount": format_amount(amount, "us"),
        "Fee": format_amount(fee, "us"),
        "Net": format_amount(net, "us"),
    }


def _shopify_files(orders: list[Order]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    file1: list[dict[str, str]] = []
    file2: list[dict[str, str]] = []
    for order in orders:
        if order.store != _STORE_SHOPIFY or not order.in_settlement:
            continue
        amount = order.item_price
        fee = _shopify_fee(amount)
        net = amount - fee
        status = vocab.SHOPIFY_STATUS_PAID
        if order.order_id in _SHOPIFY_FILE1_IDS:
            payout_date = "2026-10-07"
            target = file1
        else:
            payout_date = "2026-10-21"
            target = file2
        available_on = payout_date
        if order.extra == "pending":
            status = vocab.SHOPIFY_STATUS_PENDING
            payout_date = ""
            available_on = "2026-10-28"
        if order.extra == "net_mismatch":
            net = Decimal("19.00")
        target.append(
            _shopify_line(
                order,
                type_=vocab.SHOPIFY_TYPE_CHARGE,
                amount=amount,
                fee=fee,
                net=net,
                status=status,
                payout_date=payout_date,
                available_on=available_on,
            )
        )
    dispute_order = next(order for order in orders if order.order_id == _ID_SH_CB)
    file2.append(
        _shopify_line(
            dispute_order,
            type_=vocab.SHOPIFY_TYPE_DISPUTE,
            amount=Decimal("-35.00"),
            fee=Decimal("0.00"),
            net=Decimal("-35.00"),
            status=vocab.SHOPIFY_STATUS_PAID,
            payout_date="2026-10-21",
            available_on="2026-10-21",
            txn_date="2026-10-18 10:15:00 -0400",
        )
    )
    return file1, file2


def _sum_amounts(rows: Sequence[dict[str, str]], locale: str, column: str = "amount") -> Decimal:
    total = Decimal("0")
    for row in rows:
        total += parse_amount(row[column], locale)  # locale 只接受 us / eu
    return total


def _groups(
    us_details: Sequence[dict[str, str]],
    de_details: Sequence[dict[str, str]],
    shopify_rows: Sequence[dict[str, str]],
) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    groups: list[tuple[str, str, str]] = []

    def add(source: str, order_id: str, sku: str) -> None:
        if order_id == "":
            return
        key = (source, order_id, sku)
        if key in seen:
            return
        seen.add(key)
        groups.append(key)

    for row in [*us_details, *de_details]:
        if row["transaction-type"] in vocab.ORDER_TRANSACTION_TYPES:
            add("amazon", row["order-id"], row["sku"])
    for row in shopify_rows:
        if row["Type"] in vocab.SHOPIFY_ORDER_TYPES and row["Payout Status"].casefold() == "paid":
            add("shopify", row["Order"], "")
    return groups


def _amazon_rows(
    details: Sequence[dict[str, str]],
    order_id: str,
    *,
    description: str | None = None,
    transaction_type: str | None = None,
) -> list[int]:
    found: list[int] = []
    for index, row in enumerate(details):
        if row["order-id"] != order_id:
            continue
        if description is not None and row["amount-description"] != description:
            continue
        if transaction_type is not None and row["transaction-type"] != transaction_type:
            continue
        found.append(index + 3)
    return found


def _order_row(orders: Sequence[Order], order_id: str) -> int:
    for index, order in enumerate(orders):
        if order.order_id == order_id:
            return index + 2
    _fail(f"订单不在 orders.csv: {order_id}")
    return 0


def _shopify_rows(
    rows: Sequence[dict[str, str]],
    order_id: str,
    type_: str | None = None,
) -> list[int]:
    found: list[int] = []
    for index, row in enumerate(rows):
        if row["Order"] != order_id:
            continue
        if type_ is not None and row["Type"] != type_:
            continue
        found.append(index + 2)
    return found


def _anomaly(
    scenario: str,
    file: str,
    row_nos: list[int],
    order_id: str,
    sku: str,
    kind: str,
    note: str,
) -> dict[str, object]:
    if not row_nos:
        _fail(f"{scenario} 没有行号")
    return {
        "scenario": scenario,
        "file": file,
        "row_nos": row_nos,
        "order_id": order_id,
        "sku": sku,
        "expected_issue_kind": kind,
        "note": note,
    }


def _build_anomalies(
    orders: Sequence[Order],
    us_details: Sequence[dict[str, str]],
    de_details: Sequence[dict[str, str]],
    shop1: Sequence[dict[str, str]],
    shop2: Sequence[dict[str, str]],
    bad_sum: Decimal,
    bad_stated: Decimal,
) -> list[dict[str, object]]:
    fba_rows = _amazon_rows(us_details, _ID_NORMAL_US, description=vocab.DESC_FBA)
    if len(fba_rows) != 2:
        _fail(f"重复行应有 2 条 FBA，实际 {len(fba_rows)}")
    normal_rows = [
        *_amazon_rows(us_details, _ID_NORMAL_US, description=vocab.DESC_PRINCIPAL),
        *_amazon_rows(us_details, _ID_NORMAL_US, description=vocab.DESC_COMMISSION),
        fba_rows[0],
    ]
    us_name = vocab.FILE_AMAZON_US
    de_name = vocab.FILE_AMAZON_DE
    anomalies = [
        _anomaly(
            "normal",
            us_name,
            normal_rows,
            _ID_NORMAL_US,
            _SKU_CUP,
            "",
            "Order 的 Principal、佣金、FBA 与订单表一致，应匹配成功。代表行，不是全部正常单。",
        ),
        _anomaly(
            "fee_overcharge",
            us_name,
            _amazon_rows(us_details, _ID_FEE),
            _ID_FEE,
            _SKU_CUP,
            "FEE_OVERCHARGE?",
            "FBA 配送费 5.50 高于 fee_reference.csv 的 3.50/件。匹配仍成功。"
            "候选原因码，maken 确认前写 FEE_OVERCHARGE?。订单表第 "
            f"{_order_row(orders, _ID_FEE)} 行。",
        ),
        _anomaly(
            "in_transit",
            vocab.FILE_ORDERS,
            [_order_row(orders, _ID_IN_US)],
            _ID_IN_US,
            _SKU_CUP,
            "NOT_IN_SETTLEMENT",
            "订单日期 2026-10-25，不在任何结算/打款文件。不算错：仅超过 GRACE_DAYS=14 后才报，"
            "否则标待下期。",
        ),
        _anomaly(
            "in_transit",
            vocab.FILE_ORDERS,
            [_order_row(orders, _ID_IN_DE)],
            _ID_IN_DE,
            _SKU_PAD,
            "NOT_IN_SETTLEMENT",
            "订单日期 2026-10-31，不在任何结算/打款文件。不算错：仅超过 GRACE_DAYS=14 后才报，"
            "否则标待下期。",
        ),
        _anomaly(
            "in_transit",
            vocab.FILE_SHOPIFY_1021,
            _shopify_rows(shop2, _ID_PENDING),
            _ID_PENDING,
            _SKU_TEE,
            "NOT_IN_SETTLEMENT",
            "Payout Status=pending（待真实数据验证），当作未打款。行在打款导出里，但不算已结算。"
            "GRACE_DAYS 内标待下期，不报错。订单表第 "
            f"{_order_row(orders, _ID_PENDING)} 行。",
        ),
        _anomaly(
            "refund",
            us_name,
            _amazon_rows(us_details, _ID_REFUND),
            _ID_REFUND,
            _SKU_MUG,
            "",
            "同一订单有 Order 和 Refund，Refund 含退回的佣金。按订单号合并后匹配成功，"
            "利润里退款为负。不得因退款行把 Principal 轧差后报 AMOUNT_MISMATCH。订单表第 "
            f"{_order_row(orders, _ID_REFUND)} 行。",
        ),
        _anomaly(
            "partial_refund",
            us_name,
            _amazon_rows(us_details, _ID_PARTIAL),
            _ID_PARTIAL,
            _SKU_BAG,
            "",
            "Refund Principal 10.00 < Order Principal 60.00。Order 行 quantity-purchased 仍为 2，"
            "与订单 qty 相同。匹配成功，不得报 QTY_MISMATCH。订单表第 "
            f"{_order_row(orders, _ID_PARTIAL)} 行。",
        ),
        _anomaly(
            "chargeback",
            us_name,
            _amazon_rows(us_details, _ID_CB, transaction_type=vocab.TX_CHARGEBACK),
            _ID_CB,
            _SKU_CUP,
            "",
            "Amazon Chargeback 类交易（transaction-type 待真实数据验证）。匹配到原订单，"
            "按退款类计入利润。scenario=chargeback，便于以后单独分类。订单表第 "
            f"{_order_row(orders, _ID_CB)} 行。",
        ),
        _anomaly(
            "chargeback",
            vocab.FILE_SHOPIFY_1021,
            _shopify_rows(shop2, _ID_SH_CB, vocab.SHOPIFY_TYPE_DISPUTE),
            _ID_SH_CB,
            _SKU_TEE,
            "",
            "Shopify dispute 类交易（Type 待真实数据验证）。原 charge 在 "
            f"{vocab.FILE_SHOPIFY_1007} 第 {_shopify_rows(shop1, _ID_SH_CB)[0]} 行。"
            "匹配到原订单，按退款类计入利润。scenario=chargeback。",
        ),
        _anomaly(
            "refund_without_order",
            us_name,
            _amazon_rows(us_details, _ID_REFUND_NO_ORDER),
            _ID_REFUND_NO_ORDER,
            _SKU_CUP,
            "REFUND_WITHOUT_ORDER",
            "Refund 行的订单号不在 orders.csv。sku 在 sku_map.csv，所以不是 SKU_UNMAPPED。",
        ),
        _anomaly(
            "not_in_erp",
            us_name,
            _amazon_rows(us_details, _ID_NOT_IN_ERP),
            _ID_NOT_IN_ERP,
            _SKU_CUP,
            "NOT_IN_ERP",
            "Order 行的订单号不在 orders.csv。sku 在 sku_map.csv，所以不是 SKU_UNMAPPED。",
        ),
        _anomaly(
            "qty_mismatch",
            us_name,
            _amazon_rows(us_details, _ID_QTY, transaction_type=vocab.TX_ORDER),
            _ID_QTY,
            _SKU_MUG,
            "QTY_MISMATCH",
            "结算 quantity-purchased=1，订单 qty=3。Principal 与 item_price 一致，只报数量不符。"
            f"订单表第 {_order_row(orders, _ID_QTY)} 行。",
        ),
        _anomaly(
            "amount_mismatch",
            us_name,
            _amazon_rows(us_details, _ID_AMT, description=vocab.DESC_PRINCIPAL),
            _ID_AMT,
            _SKU_BAG,
            "AMOUNT_MISMATCH",
            "Order Principal 22.00 ≠ 订单 item_price 25.00。数量一致。订单表第 "
            f"{_order_row(orders, _ID_AMT)} 行。",
        ),
        _anomaly(
            "sku_unmapped",
            us_name,
            _amazon_rows(us_details, _ID_UNMAPPED),
            _ID_UNMAPPED,
            _SKU_UNMAPPED,
            "SKU_UNMAPPED",
            "结算 sku 不在 sku_map.csv。订单在 orders.csv 第 "
            f"{_order_row(orders, _ID_UNMAPPED)} 行。"
            "按实施方案 6.2 先查映射。期望 SKU_UNMAPPED。",
        ),
        _anomaly(
            "cost_missing",
            us_name,
            _amazon_rows(us_details, _ID_COST),
            _ID_COST,
            _SKU_GAP,
            "COST_MISSING",
            "内部 SKU INT-COST-GAP 在 costs.csv 只有生效日期 2026-11-01。"
            "不覆盖订单日期 2026-10-06。"
            "对账匹配成功，利润计算时报缺成本。订单表第 "
            f"{_order_row(orders, _ID_COST)} 行。",
        ),
        _anomaly(
            "fx_missing",
            de_name,
            _amazon_rows(de_details, _ID_FX),
            _ID_FX,
            _SKU_BOT,
            "FX_MISSING",
            "用 fx_rates_missing_eur.csv 代替 fx_rates.csv 时，DE 店铺 2026-10 没有 EUR→CNY。"
            "正常汇率表有该汇率。匹配成功，W3 利润计算才产生。金额原文含 95,00。订单表第 "
            f"{_order_row(orders, _ID_FX)} 行。",
        ),
        _anomaly(
            "unknown_fee_type",
            us_name,
            [
                index + 3
                for index, row in enumerate(us_details)
                if row["amount-description"] == vocab.DESC_UNKNOWN
            ],
            "",
            "",
            "UNKNOWN_FEE_TYPE",
            "amount-description=SyntheticUnknownFee，不在 sample_vocab.KNOWN_FEE_PAIRS。"
            "transaction-type=other-transaction，非订单类，不进匹配率分母。不丢行。",
        ),
        _anomaly(
            "settlement_unbalanced",
            vocab.FILE_AMAZON_UNBALANCED,
            [2],
            "",
            "",
            "SETTLEMENT_UNBALANCED",
            "汇总行 total-amount "
            f"{format_amount(bad_stated, 'us')} ≠ 明细 amount 之和 {format_amount(bad_sum, 'us')}。"
            "该文件不进入匹配率分母。",
        ),
        _anomaly(
            "shopify_net_mismatch",
            vocab.FILE_SHOPIFY_1021,
            _shopify_rows(shop2, _ID_NET),
            _ID_NET,
            _SKU_TEE,
            "AMOUNT_MISMATCH",
            "Net 19.00 ≠ Amount 20.00 − Fee 0.40 = 19.60。订单仍在 orders.csv，"
            "但这条 AMOUNT_MISMATCH 计入未匹配组。订单表第 "
            f"{_order_row(orders, _ID_NET)} 行。",
        ),
        _anomaly(
            "duplicate_row",
            us_name,
            [fba_rows[1]],
            _ID_NORMAL_US,
            _SKU_CUP,
            "DUPLICATE_ROW",
            f"第 {fba_rows[1]} 行与第 {fba_rows[0]} 行完全相同。第二行是重复行。"
            "文件总额含这两行。匹配率不把重复行另计一组。",
        ),
    ]
    found = {str(item["scenario"]) for item in anomalies}
    missing = [name for name in vocab.REQUIRED_SCENARIOS if name not in found]
    if missing:
        _fail(f"场景未覆盖: {missing}")
    return anomalies


def _cost_rows() -> list[list[str]]:
    # 生效日期起生效，直到同一内部 SKU 的下一条（不含）。推断。
    raw = (
        ("INT-CUP-500", Decimal("12.00"), Decimal("2.00"), "CNY", "2026-01-01"),
        ("INT-CUP-500", Decimal("13.50"), Decimal("2.20"), "CNY", "2026-10-10"),
        ("INT-MUG-300", Decimal("8.00"), Decimal("1.50"), "CNY", "2026-01-01"),
        ("INT-BAG-01", Decimal("6.50"), Decimal("1.20"), "CNY", "2026-01-01"),
        ("INT-BOT-750", Decimal("15.00"), Decimal("3.00"), "CNY", "2026-01-01"),
        ("INT-PAD-A5", Decimal("4.00"), Decimal("0.80"), "CNY", "2026-01-01"),
        ("INT-TEE-M", Decimal("20.00"), Decimal("2.50"), "CNY", "2026-01-01"),
        ("INT-COST-GAP", Decimal("9.00"), Decimal("1.00"), "CNY", "2026-11-01"),
    )
    return [
        [sku, format_amount(purchase, "us"), format_amount(freight, "us"), currency, effective]
        for sku, purchase, freight, currency, effective in raw
    ]


def _fx_rows(*, drop_eur: bool) -> list[list[str]]:
    rows = [
        ["2026-10", "USD", "CNY", format_rate(Decimal("7.25000000"))],
        ["2026-10", "EUR", "CNY", format_rate(Decimal("7.85000000"))],
    ]
    if drop_eur:
        return [row for row in rows if row[1] != "EUR"]
    return rows


def _order_table(orders: Sequence[Order]) -> list[list[str]]:
    return [
        [
            order.order_id,
            order.order_item_id,
            order.store,
            order.platform_sku,
            str(order.qty),
            order.order_date,
            format_amount(order.item_price, "us"),
            order.currency,
        ]
        for order in orders
    ]


def _sku_map_rows(skus: dict[str, Sku]) -> list[list[str]]:
    return [
        [sku.store, sku.platform_sku, sku.internal_sku, sku.title]
        for sku in skus.values()
        if sku.mapped
    ]


def _fee_rows(skus: dict[str, Sku]) -> list[list[str]]:
    rows: list[list[str]] = []
    for sku in skus.values():
        if sku.fba_fee is None:
            continue
        rows.append([sku.platform_sku, sku.currency, format_amount(sku.fba_fee, "us")])
    return rows


def reference_profit() -> list[dict[str, str]]:
    """Return the independent synthetic profit reference rows.

    The checked-in CSV is data produced from the generator's fixed scenarios;
    it is never calculated by importing ``crosserp.profit``.
    """
    source = (
        Path(__file__).resolve().parents[1] / "samples" / "synthetic" / vocab.FILE_PROFIT_EXPECTED
    )
    with source.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_table(
    path: Path, header: Sequence[str], rows: Sequence[Sequence[str]], delimiter: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter, lineterminator="\n")
        writer.writerow(list(header))
        writer.writerows(rows)


def _write_dicts(
    path: Path, header: Sequence[str], rows: Sequence[dict[str, str]], delimiter: str
) -> None:
    table = [[row[column] for column in header] for row in rows]
    _write_table(path, header, table, delimiter)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: object) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _fix_core_xml(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    text = re.sub(
        r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
        rf"\g<1>{_FIXED_STAMP}\g<2>",
        text,
        count=1,
    )
    text = re.sub(
        r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
        rf"\g<1>{_FIXED_STAMP}\g<2>",
        text,
        count=1,
    )
    return text.encode("utf-8")


def _write_xlsx(path: Path, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        _fail("openpyxl 没有活动表")
    sheet.title = "Sheet1"
    sheet.append(list(header))
    for row in rows:
        sheet.append(list(row))
    workbook.properties.creator = "crosserp-sample-generator"
    workbook.properties.lastModifiedBy = "crosserp-sample-generator"
    workbook.properties.title = path.name
    workbook.properties.created = datetime(2026, 11, 9, 0, 0, 0)
    workbook.properties.modified = datetime(2026, 11, 9, 0, 0, 0)
    buffer = BytesIO()
    workbook.save(buffer)
    source = ZipFile(BytesIO(buffer.getvalue()))
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as target:
        for info in source.infolist():
            if info.is_dir():
                continue
            payload = source.read(info.filename)
            if info.filename == "docProps/core.xml":
                payload = _fix_core_xml(payload)
            cloned = ZipInfo(filename=info.filename, date_time=_ZIP_DATE)
            cloned.compress_type = ZIP_DEFLATED
            cloned.external_attr = info.external_attr
            target.writestr(cloned, payload)
    source.close()


def _assert_text(path: Path) -> None:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail(f"{path.name} 含 UTF-8 BOM")
    if b"\r" in raw:
        _fail(f"{path.name} 行尾不是 LF")


def _mapping_yaml() -> str:
    return """# 合成订单列映射。右边是本生成器的中性列名，不是领星/赛狐真实表头。
target: order_line
source_name: synthetic_orders
sheet: 0
header_row: 1
encoding: utf-8-sig
amount_locale: us
date_formats:
  - "%Y-%m-%d"
timezone: UTC
columns:
  platform_order_id: order_id
  order_item_id: order_item_id
  store: store
  platform_sku: platform_sku
  qty: qty
  order_date: order_date
  item_price: item_price
  currency: currency
"""


def _readme() -> str:
    return """# 合成样本

固定种子 `20261109` 生成。金额是 Decimal 合成值。
不是真实卖家数据。也不是亚马逊或 Shopify 的真实费率。

平台取值集中在 `scripts/sample_vocab.py`。每个值都注明「待真实数据验证」。
这不是平台字段全集。仓储费、移除费、FBA 赔偿、促销没有生成。

## 重新生成

在仓库根目录：

```bash
uv run python scripts/gen_samples.py --out samples/synthetic
```

不用 uv 时，把 `src` 放进 `PYTHONPATH`，用项目解释器运行同一脚本。
改生成器后必须重新生成并提交。`EXPECTED.md` 会一起更新。

## 读文件

- csv/tsv 是 UTF-8，无 BOM，行尾 LF。Excel 若中文乱码，用「数据 → 从文本/CSV」并选择 UTF-8。
- `amazon_de_*.tsv` 金额是 `95,00` 这种逗号小数，没有千分位。导入时分隔符选 Tab。
- `orders.csv` 一律用点小数（`amount_locale: us`），币种看 `currency` 列。
- xlsx 的金额单元格是文本，避免写成 float。
- `amazon_us_unbalanced.tsv` 故意不平，不进入匹配率分母。
"""


def _expected_md(anomalies: Sequence[dict[str, object]], summary: dict[str, object]) -> str:
    lines = [
        "# 合成样本标准答案",
        "",
        "种子 `20261109`。金额是合成值，不是真实卖家数据，也不是平台真实费率。",
        "平台取值见 `scripts/sample_vocab.py`，一律「待真实数据验证」。",
        "行号从 1 起，表头是第 1 行。",
        "",
        "## 匹配率",
        "",
        f"- 定义：{summary['match_rate_definition']}",
        f"- 订单类结算行组数：{summary['order_type_group_count']}",
        f"- 已匹配：{summary['matched_order_type_group_count']}",
        f"- 未匹配：{summary['unmatched_order_type_group_count']}",
        f"- 预期匹配率：{summary['match_rate']}（≥ 0.95）",
        f"- 未匹配占比：{summary['unmatched_ratio']}（≤ 0.05）",
        f"- GRACE_DAYS：{summary['grace_days']}",
        "",
        "## 核对时不要误判",
        "",
        "- 全额退款、部分退款、拒付应匹配成功。比较金额时只用 Order 的 Principal，"
        "不要把 Refund/Chargeback 的 Principal 轧差后再和 item_price 比。推断，与场景表一致。",
        "- 同一订单多行的 quantity-purchased 重复填写同一数量。"
        "对账按订单项取一次。不要把费用行数量加总。推断。待真实数据验证。",
        "- 部分退款的 Refund 行 quantity-purchased 为 0。"
        "Order 行数量与订单 qty 相同。不得报 QTY_MISMATCH。",
        "- 10/25 与 10/31 的订单不在任何结算里。当前应标待下期，不是错。",
        "- `FEE_OVERCHARGE?` 是候选原因码，确认前不要写进正式枚举。",
        "",
        "## 场景",
        "",
    ]
    for item in anomalies:
        rows = item["row_nos"]
        assert isinstance(rows, list)
        row_text = ", ".join(str(number) for number in rows)
        lines.extend(
            [
                f"### {item['scenario']}",
                "",
                f"- 文件：`{item['file']}`",
                f"- 行号：{row_text}",
                f"- 订单号：{item['order_id'] or '（无）'}",
                f"- SKU：{item['sku'] or '（无）'}",
                f"- 期望原因码：{item['expected_issue_kind'] or '（匹配成功，无异常）'}",
                f"- 说明：{item['note']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 本样本没有的费用",
            "",
            "不是全集。没有生成仓储费、移除费、FBA 赔偿、促销。"
            "真实文件里如果有，应进未知费用。不要猜。",
            "",
        ]
    )
    return "\n".join(lines)


def _file_entry(data_rows: int, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"data_rows": data_rows}
    payload.update(extra)
    return payload


def _settlement_entry(
    file: str,
    settlement_id: str,
    currency: str,
    locale: str,
    total: Decimal,
    line_sum: Decimal,
    *,
    data_rows: int,
    transaction_rows: int,
    balanced: bool,
) -> dict[str, object]:
    return {
        "file": file,
        "settlement_id": settlement_id,
        "currency": currency,
        "locale": locale,
        "total_amount": format_amount(total, "us"),
        "total_amount_display": format_amount(total, locale),
        "line_amount_sum": format_amount(line_sum, "us"),
        "balanced": balanced,
        "data_rows": data_rows,
        "transaction_rows": transaction_rows,
    }


def _check_amounts(rows: Sequence[dict[str, str]], column: str, locale: str) -> None:
    pattern = re.compile(r"^-?\d+\.\d{2}$" if locale == "us" else r"^-?\d+,\d{2}$")
    for row in rows:
        text = row[column]
        if text and pattern.fullmatch(text) is None:
            _fail(f"金额格式不对: {text}")


def _check_invariants(
    orders: Sequence[Order],
    us_details: Sequence[dict[str, str]],
    de_details: Sequence[dict[str, str]],
    shop1: Sequence[dict[str, str]],
    shop2: Sequence[dict[str, str]],
    skus: dict[str, Sku],
    us_sum: Decimal,
    de_sum: Decimal,
    bad_sum: Decimal,
    bad_stated: Decimal,
) -> tuple[list[tuple[str, str, str]], int, int]:
    if locale_for(vocab.MARKETPLACE_DE, "EUR") != "eu":
        _fail("Amazon.de / EUR 应使用 eu 小数格式")
    if locale_for(vocab.MARKETPLACE_US, "USD") != "us":
        _fail("Amazon.com / USD 应使用 us 小数格式")
    if any(order.order_id in {_ID_IN_US, _ID_IN_DE} and order.in_settlement for order in orders):
        _fail("在途订单不应标记为已进结算")
    amazon_ids = {row["order-id"] for row in [*us_details, *de_details] if row["order-id"]}
    shopify_ids = {row["Order"] for row in [*shop1, *shop2] if row["Order"]}
    if {_ID_IN_US, _ID_IN_DE} & (amazon_ids | shopify_ids):
        _fail("在途订单出现在结算文件里")
    if not any(row["amount"] == "95,00" for row in de_details):
        _fail("DE 文件缺少 95,00")
    if not any("🍵" in sku.title for sku in skus.values()):
        _fail("sku 标题缺少中文和 emoji")
    fba_rows = [
        row
        for row in us_details
        if row["order-id"] == _ID_NORMAL_US and row["amount-description"] == vocab.DESC_FBA
    ]
    if len(fba_rows) != 2 or fba_rows[0] != fba_rows[1]:
        _fail("重复行不是原样两份")
    if bad_stated == bad_sum:
        _fail("不平衡文件的总额不应等于明细之和")
    if parse_amount(format_amount(us_sum, "us"), "us") != us_sum:
        _fail("US 总额格式化后无法还原")
    if parse_amount(format_amount(de_sum, "eu"), "eu") != de_sum:
        _fail("DE 总额格式化后无法还原")
    _check_amounts(us_details, "amount", "us")
    _check_amounts(de_details, "amount", "eu")
    known = {(pair[0], pair[1]) for pair in vocab.KNOWN_FEE_PAIRS}
    if (vocab.AMOUNT_TYPE_FEE, vocab.DESC_UNKNOWN) in known:
        _fail("未知费用被写进了已知组合")
    groups = _groups(us_details, de_details, [*shop1, *shop2])
    unmatched = [key for key in groups if key[1] in _UNMATCHED_ORDER_IDS]
    missing = _UNMATCHED_ORDER_IDS.difference(key[1] for key in unmatched)
    if missing or len(unmatched) != len(_UNMATCHED_ORDER_IDS):
        _fail(f"未匹配组不符: {unmatched} missing={sorted(missing)}")
    matched = len(groups) - len(unmatched)
    total = len(groups)
    if total == 0:
        _fail("没有订单类结算行组")
    rate = Decimal(matched) / Decimal(total)
    ratio = Decimal(len(unmatched)) / Decimal(total)
    if rate < Decimal("0.95") or ratio > Decimal("0.05"):
        _fail(
            f"预期匹配率 {rate}，未匹配占比 {ratio}，组数 {total}，未匹配 {len(unmatched)}。"
            "需要 ≥0.95 且未匹配不超过 5%。"
        )
    return groups, matched, len(unmatched)


def generate(out: Path) -> dict[str, object]:
    """生成全部合成样本。失败时抛 SystemExit，不写一半答案。"""
    rng = random.Random(vocab.SEED)
    skus = _skus()
    orders = _build_orders(rng)
    us_details = _us_details(orders, skus)
    de_details = _de_details(orders, skus)
    bad_details = _unbalanced_details(skus)
    shop1, shop2 = _shopify_files(orders)
    us_sum = _sum_amounts(us_details, "us")
    de_sum = _sum_amounts(de_details, "eu")
    bad_sum = _sum_amounts(bad_details, "us")
    bad_stated = bad_sum + _UNBALANCED_DELTA
    groups, matched, unmatched = _check_invariants(
        orders,
        us_details,
        de_details,
        shop1,
        shop2,
        skus,
        us_sum,
        de_sum,
        bad_sum,
        bad_stated,
    )
    anomalies = _build_anomalies(orders, us_details, de_details, shop1, shop2, bad_sum, bad_stated)
    rate = Decimal(matched) / Decimal(len(groups))
    ratio = Decimal(unmatched) / Decimal(len(groups))
    shop1_net = _sum_amounts(shop1, "us", "Net")
    shop2_net = _sum_amounts(shop2, "us", "Net")
    cost_rows = _cost_rows()
    fx_rows = _fx_rows(drop_eur=False)
    fx_missing = _fx_rows(drop_eur=True)
    order_rows = _order_table(orders)
    sku_rows = _sku_map_rows(skus)
    fee_rows = _fee_rows(skus)
    us_written = [
        _summary_row(_SETTLEMENT_US, vocab.MARKETPLACE_US, "USD", us_sum, "us"),
        *us_details,
    ]
    de_written = [
        _summary_row(_SETTLEMENT_DE, vocab.MARKETPLACE_DE, "EUR", de_sum, "eu"),
        *de_details,
    ]
    bad_written = [
        _summary_row(
            _SETTLEMENT_UNBALANCED,
            vocab.MARKETPLACE_US,
            "USD",
            bad_stated,
            "us",
        ),
        *bad_details,
    ]
    summary: dict[str, object] = {
        "seed": vocab.SEED,
        "grace_days": vocab.GRACE_DAYS,
        "match_rate": format(rate, "f"),
        "order_type_group_count": len(groups),
        "matched_order_type_group_count": matched,
        "unmatched_order_type_group_count": unmatched,
        "unmatched_ratio": format(ratio, "f"),
        "unmatched_order_ids": sorted(_UNMATCHED_ORDER_IDS),
        "match_rate_definition": _MATCH_RATE_DEFINITION,
        "files": {
            vocab.FILE_ORDERS: _file_entry(len(order_rows)),
            vocab.FILE_MAPPING: _file_entry(0, note="YAML 列映射，不是表格"),
            vocab.FILE_COSTS: _file_entry(len(cost_rows)),
            vocab.FILE_COSTS_XLSX: _file_entry(len(cost_rows)),
            vocab.FILE_FX: _file_entry(len(fx_rows)),
            vocab.FILE_FX_XLSX: _file_entry(len(fx_rows)),
            vocab.FILE_FX_MISSING_EUR: _file_entry(len(fx_missing)),
            vocab.FILE_SKU_MAP: _file_entry(len(sku_rows)),
            vocab.FILE_FEE_REFERENCE: _file_entry(len(fee_rows)),
            vocab.FILE_AMAZON_US: _file_entry(
                len(us_written), total_amount=format_amount(us_sum, "us")
            ),
            vocab.FILE_AMAZON_DE: _file_entry(
                len(de_written), total_amount=format_amount(de_sum, "eu")
            ),
            vocab.FILE_AMAZON_UNBALANCED: _file_entry(
                len(bad_written),
                total_amount=format_amount(bad_stated, "us"),
                line_amount_sum=format_amount(bad_sum, "us"),
                balanced=False,
            ),
            vocab.FILE_SHOPIFY_1007: _file_entry(
                len(shop1), total_amount=format_amount(shop1_net, "us")
            ),
            vocab.FILE_SHOPIFY_1021: _file_entry(
                len(shop2), total_amount=format_amount(shop2_net, "us")
            ),
            vocab.FILE_EXPECTED: _file_entry(0, note="说明文件"),
            vocab.FILE_README: _file_entry(0, note="说明文件"),
            vocab.FILE_ANOMALIES: _file_entry(len(anomalies)),
            vocab.FILE_SUMMARY: _file_entry(1, note="本文件"),
            vocab.FILE_PROFIT_EXPECTED: _file_entry(20, note="独立 Decimal 参考答案"),
        },
        "settlements": [
            _settlement_entry(
                vocab.FILE_AMAZON_US,
                _SETTLEMENT_US,
                "USD",
                "us",
                us_sum,
                us_sum,
                data_rows=len(us_written),
                transaction_rows=len(us_details),
                balanced=True,
            ),
            _settlement_entry(
                vocab.FILE_AMAZON_DE,
                _SETTLEMENT_DE,
                "EUR",
                "eu",
                de_sum,
                de_sum,
                data_rows=len(de_written),
                transaction_rows=len(de_details),
                balanced=True,
            ),
            _settlement_entry(
                vocab.FILE_AMAZON_UNBALANCED,
                _SETTLEMENT_UNBALANCED,
                "USD",
                "us",
                bad_stated,
                bad_sum,
                data_rows=len(bad_written),
                transaction_rows=len(bad_details),
                balanced=False,
            ),
            {
                "file": vocab.FILE_SHOPIFY_1007,
                "currency": "USD",
                "locale": "us",
                "total_amount": format_amount(shop1_net, "us"),
                "total_basis": "sum_of_net",
                "data_rows": len(shop1),
                "note": "文件没有汇总行。total 为 ΣNet。推断，待真实数据验证。",
            },
            {
                "file": vocab.FILE_SHOPIFY_1021,
                "currency": "USD",
                "locale": "us",
                "total_amount": format_amount(shop2_net, "us"),
                "total_basis": "sum_of_net",
                "data_rows": len(shop2),
                "note": "文件没有汇总行。total 为 ΣNet，含故意写错的 Net。推断，待真实数据验证。",
            },
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    _write_table(out / vocab.FILE_ORDERS, vocab.ORDER_COLUMNS, order_rows, ",")
    _write_text(out / vocab.FILE_MAPPING, _mapping_yaml())
    _write_table(out / vocab.FILE_COSTS, vocab.COST_COLUMNS, cost_rows, ",")
    _write_xlsx(out / vocab.FILE_COSTS_XLSX, vocab.COST_COLUMNS, cost_rows)
    _write_table(out / vocab.FILE_FX, vocab.FX_COLUMNS, fx_rows, ",")
    _write_xlsx(out / vocab.FILE_FX_XLSX, vocab.FX_COLUMNS, fx_rows)
    _write_table(out / vocab.FILE_FX_MISSING_EUR, vocab.FX_COLUMNS, fx_missing, ",")
    _write_table(out / vocab.FILE_SKU_MAP, vocab.SKU_MAP_COLUMNS, sku_rows, ",")
    _write_table(out / vocab.FILE_FEE_REFERENCE, vocab.FEE_REFERENCE_COLUMNS, fee_rows, ",")
    _write_dicts(out / vocab.FILE_AMAZON_US, vocab.AMAZON_V2_COLUMNS, us_written, "\t")
    _write_dicts(out / vocab.FILE_AMAZON_DE, vocab.AMAZON_V2_COLUMNS, de_written, "\t")
    _write_dicts(out / vocab.FILE_AMAZON_UNBALANCED, vocab.AMAZON_V2_COLUMNS, bad_written, "\t")
    _write_dicts(out / vocab.FILE_SHOPIFY_1007, vocab.SHOPIFY_COLUMNS, shop1, ",")
    _write_dicts(out / vocab.FILE_SHOPIFY_1021, vocab.SHOPIFY_COLUMNS, shop2, ",")
    _write_json(out / vocab.FILE_ANOMALIES, anomalies)
    _write_json(out / vocab.FILE_SUMMARY, summary)
    profit_rows = reference_profit()
    if profit_rows:
        _write_dicts(out / vocab.FILE_PROFIT_EXPECTED, tuple(profit_rows[0]), profit_rows, ",")
    _write_text(out / vocab.FILE_EXPECTED, _expected_md(anomalies, summary))
    _write_text(out / vocab.FILE_README, _readme())
    for path in out.rglob("*"):
        if path.is_file() and path.suffix != ".xlsx":
            _assert_text(path)
    return summary


def _print_summary(summary: dict[str, object]) -> None:
    files = summary["files"]
    assert isinstance(files, dict)
    print(f"种子: {summary['seed']}")
    for name in sorted(files):
        info = files[name]
        assert isinstance(info, dict)
        extra = ""
        if "total_amount" in info:
            extra = f" total={info['total_amount']}"
        if info.get("balanced") is False:
            extra += " balanced=false"
        print(f"{name}: {info['data_rows']} 数据行{extra}")
    print(
        "预期匹配率 ≥95%："
        f"实际 {summary['match_rate']}，"
        f"订单类结算行组 {summary['order_type_group_count']}，"
        f"已匹配 {summary['matched_order_type_group_count']}，"
        f"未匹配 {summary['unmatched_order_type_group_count']}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 CrossERP 合成样本。种子固定为 20261109。")
    parser.add_argument(
        "--out", default="samples/synthetic", help="输出目录，默认 samples/synthetic"
    )
    parser.add_argument("--check", action="store_true", help="只检查现有目录是否可复现，不改文件")
    args = parser.parse_args(list(argv) if argv is not None else None)
    destination = Path(args.out)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="crosserp-samples-") as temporary:
            generated = Path(temporary)
            summary = generate(generated)
            expected = sorted(path.relative_to(generated) for path in generated.rglob("*"))
            actual = sorted(path.relative_to(destination) for path in destination.rglob("*"))
            if expected != actual:
                print("样本目录文件列表与固定种子生成结果不一致。", file=sys.stderr)
                return 1
            for relative in expected:
                left = generated / relative
                right = destination / relative
                if left.is_file() and left.read_bytes() != right.read_bytes():
                    print(f"样本文件与固定种子生成结果不一致: {relative}", file=sys.stderr)
                    return 1
    else:
        summary = generate(destination)
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
