"""Shopify Payments 打款 CSV。按表头名读。不调 API。

没有 Payout ID 时按 Payout Date 分组。这是推断。待真实数据验证。
settlement_line 没有状态列。Payout Status 写在 amount_description。前缀 payout_status=。
明细 amount 用该行 Net。这样各组 total = ΣNet。Amount 与 Fee 留在 raw_row。
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from crosserp.connectors.base import SourceKind
from crosserp.core.enums import IssueKind, Platform
from crosserp.core.errors import AmountParseError
from crosserp.core.models import (
    CanonicalRecord,
    ColumnMapping,
    IssueRec,
    RawRow,
    SettlementHeader,
    SettlementLineRec,
)
from crosserp.core.money import Locale, locale_for, parse_amount

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Transaction Date",
    "Type",
    "Order",
    "Card Brand",
    "Card Source",
    "Payout Status",
    "Payout Date",
    "Available On",
    "Amount",
    "Fee",
    "Net",
)
_SNIFF_COLUMNS: tuple[str, ...] = ("Payout Date", "Amount", "Fee", "Net", "Type")
_EXTRA_KEY = "__extra_values__"
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_TXN_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
)
_PAYOUT_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
)


@dataclass(frozen=True)
class _GroupPlan:
    external_id: str
    currency: str
    total: Decimal
    period_start: datetime
    period_end: datetime
    deposit_date: datetime | None
    marketplace: str
    store_name: str


@dataclass(frozen=True)
class _RowPlan:
    row_no: int
    payload: dict[str, str]
    error: str | None
    group_key: str
    external_id: str
    currency: str
    order_id: str | None
    type_raw: str
    transaction_type: str
    known_type: bool
    payout_status: str
    amount: Decimal | None
    fee: Decimal | None
    net: Decimal | None
    posted_at: datetime | None


class ShopifyPayoutsConnector:
    """读 Shopify Finance > Payouts 交易 CSV。"""

    id = "shopify.payouts"
    kind: SourceKind = "payout"
    version = "0.1.0"

    def __init__(self) -> None:
        self._type_map = _load_type_map(Path(__file__).with_name("type_map.yaml"))
        self._rows: dict[int, _RowPlan] = {}
        self._groups: dict[str, _GroupPlan] = {}
        self._header_rows: set[int] = set()

    def sniff(self, path: Path) -> float:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header_line = handle.readline()
        except OSError:
            return 0.0
        if header_line.strip() == "":
            return 0.0
        try:
            header = next(csv.reader([header_line]))
        except csv.Error:
            return 0.0
        names = {cell.strip() for cell in header}
        if all(name in names for name in _SNIFF_COLUMNS):
            return 0.9
        return 0.0

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        self._rows = {}
        self._groups = {}
        self._header_rows = set()
        plans, groups, header_rows = _prepare(path, mapping, self._type_map)
        self._rows = {item.row_no: item for item in plans}
        self._groups = groups
        self._header_rows = header_rows
        for item in plans:
            yield RawRow(row_no=item.row_no, payload=item.payload, source_file=path.name)

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        prepared = self._rows.get(row.row_no)
        if prepared is None:
            raise ValueError(f"第 {row.row_no} 行没有解析上下文。请先读取同一文件。")
        records: list[CanonicalRecord] = []
        if row.row_no in self._header_rows:
            records.append(_header(self._groups[prepared.group_key]))
        if prepared.error is not None:
            records.append(
                IssueRec(
                    issue_kind=IssueKind.PARSE_ERROR,
                    severity="error",
                    detail_json={
                        "row_no": row.row_no,
                        "error": prepared.error,
                        "raw": row.payload,
                    },
                )
            )
            return records
        records.append(_line(prepared))
        mismatch = _mismatch_issue(prepared)
        if mismatch is not None:
            records.append(mismatch)
        if not prepared.known_type:
            records.append(_unknown_type_issue(prepared))
        return records


def _load_type_map(path: Path) -> dict[str, str]:
    loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("type_map.yaml 必须是映射")
    known = loaded.get("known")
    if not isinstance(known, dict):
        raise TypeError("type_map.yaml 缺少 known")
    mapped: dict[str, str] = {}
    for key, value in known.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise TypeError("type_map.yaml 的 known 格式不对")
        transaction_type = value.get("transaction_type")
        if not isinstance(transaction_type, str) or transaction_type.strip() == "":
            raise TypeError(f"type_map.yaml 的 {key} 缺少 transaction_type")
        mapped[key.casefold()] = transaction_type.strip()
    if not mapped:
        raise TypeError("type_map.yaml 没有已知 Type")
    return mapped


def _prepare(
    path: Path,
    mapping: ColumnMapping | None,
    type_map: dict[str, str],
) -> tuple[list[_RowPlan], dict[str, _GroupPlan], set[int]]:
    headers, table = _read_table(path)
    by_payout_id = "Payout ID" in headers
    has_currency = "Currency" in headers
    default_currency = _default_currency(mapping)
    forced_locale = None if mapping is None else mapping.amount_locale
    marketplace, store_name = _store_identity(mapping)
    located = [_locate(row_no, payload, by_payout_id) for row_no, payload in table]
    currencies = _currencies(located, has_currency, default_currency)
    _reject_mixed_file_currency(currencies)
    plans = [
        _parse_located(item, currencies[item.group_key], forced_locale, type_map)
        for item in located
    ]
    groups, header_rows = _groups(plans, currencies, marketplace, store_name)
    return plans, groups, header_rows


@dataclass(frozen=True)
class _Located:
    row_no: int
    payload: dict[str, str]
    group_key: str
    external_id: str


def _read_table(path: Path) -> tuple[set[str], list[tuple[int, dict[str, str]]]]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ValueError(f"无法打开文件。{exc}") from exc
    with handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("文件没有表头。") from exc
        except csv.Error as exc:
            raise ValueError(f"无法读取表头。{exc}") from exc
        names = [cell.strip() for cell in header]
        if any(name == "" for name in names):
            raise ValueError("表头有空列名。无法按列名取值。")
        if len(names) != len(set(names)):
            raise ValueError("表头有重复列。无法按列名取值。")
        missing = [name for name in _REQUIRED_COLUMNS if name not in set(names)]
        if missing:
            raise ValueError("缺少基础列。" + "、".join(missing) + "。")
        rows: list[tuple[int, dict[str, str]]] = []
        for row_no, cells in enumerate(reader, start=2):
            if cells == []:
                continue
            payload, extras = _cells_to_payload(names, cells)
            if extras:
                payload[_EXTRA_KEY] = "|".join(extras)
            rows.append((row_no, payload))
    return set(names), rows


def _cells_to_payload(names: list[str], cells: list[str]) -> tuple[dict[str, str], list[str]]:
    extras = cells[len(names) :]
    width = cells[: len(names)]
    if len(width) < len(names):
        width = [*width, *[""] * (len(names) - len(width))]
    return {name: width[index] for index, name in enumerate(names)}, extras


def _locate(row_no: int, payload: dict[str, str], by_payout_id: bool) -> _Located:
    if by_payout_id:
        raw = payload.get("Payout ID", "").strip()
        external_id = raw if raw else "payout-id:missing"
        group_key = f"id:{raw}"
    else:
        raw = payload.get("Payout Date", "").strip()
        external_id = f"payout-date:{raw}" if raw else "payout-date:missing"
        group_key = f"date:{raw}"
    if len(external_id) > 64:
        raise ValueError(f"第 {row_no} 行的打款标识超过 64 个字符。不能截断。")
    return _Located(row_no, payload, group_key, external_id)


def _default_currency(mapping: ColumnMapping | None) -> str | None:
    if mapping is None:
        return None
    raw = mapping.defaults.get("currency", "").strip().upper()
    if raw == "":
        return None
    if _CURRENCY_RE.fullmatch(raw) is None:
        raise ValueError(f"默认币种无法识别 {raw}。")
    return raw


def _store_identity(mapping: ColumnMapping | None) -> tuple[str, str]:
    # 打款文件没有店铺列。默认名是推断。调用方可用 mapping.defaults 覆盖。
    marketplace = "shopify"
    store_name = "Shopify"
    if mapping is not None:
        custom_market = mapping.defaults.get("marketplace", "").strip()
        custom_name = mapping.defaults.get("store_name", "").strip()
        if custom_market:
            marketplace = custom_market
        if custom_name:
            store_name = custom_name
    if marketplace == "" or store_name == "" or len(marketplace) > 64 or len(store_name) > 255:
        raise ValueError("店铺名或站点为空。或超过长度限制。")
    return marketplace, store_name


def _currencies(
    located: list[_Located],
    has_currency: bool,
    default_currency: str | None,
) -> dict[str, str]:
    found: dict[str, set[str]] = defaultdict(set)
    keys: set[str] = set()
    for item in located:
        keys.add(item.group_key)
        if not has_currency:
            continue
        raw = item.payload.get("Currency", "").strip().upper()
        if raw == "":
            continue
        if _CURRENCY_RE.fullmatch(raw) is None:
            raise ValueError(f"第 {item.row_no} 行币种无法识别 {raw}。")
        found[item.group_key].add(raw)
    resolved: dict[str, str] = {}
    for key in keys:
        values = found.get(key, set())
        if len(values) > 1:
            listed = "、".join(sorted(values))
            raise ValueError(f"同一打款分组有多种币种 {listed}。不能相加。")
        if len(values) == 1:
            resolved[key] = next(iter(values))
            continue
        if default_currency is None:
            raise ValueError(
                "无法确定币种。文件没有可用的 Currency。也没有 --currency 或店铺默认币种。"
                "请用 --currency 指定。或先设置店铺默认币种。"
            )
        resolved[key] = default_currency
    return resolved


def _reject_mixed_file_currency(currencies: dict[str, str]) -> None:
    values = set(currencies.values())
    if len(values) <= 1:
        return
    listed = "、".join(sorted(values))
    raise ValueError(f"文件里有多种币种 {listed}。当前一个店铺只记一种币种。不猜测拆店。")


def _parse_located(
    item: _Located,
    currency: str,
    forced_locale: Locale | None,
    type_map: dict[str, str],
) -> _RowPlan:
    error: str | None = None
    amount: Decimal | None = None
    fee: Decimal | None = None
    net: Decimal | None = None
    posted_at: datetime | None = None
    type_raw = item.payload.get("Type", "").strip()
    transaction_type = type_raw
    known_type = False
    order_id = _order_id(item.payload.get("Order", ""))
    payout_status = item.payload.get("Payout Status", "").strip()
    try:
        posted_at = _parse_transaction_date(item.payload.get("Transaction Date", ""))
        amount = _parse_money(item.payload.get("Amount", ""), currency, forced_locale)
        fee = _parse_money(item.payload.get("Fee", ""), currency, forced_locale)
        net = _parse_money(item.payload.get("Net", ""), currency, forced_locale)
        _parse_payout_date(item.payload.get("Payout Date", ""))
        transaction_type, known_type = _map_type(type_raw, type_map)
        _check_lengths(transaction_type, type_raw, order_id, payout_status)
    except ValueError as exc:
        error = str(exc)
    return _RowPlan(
        row_no=item.row_no,
        payload=item.payload,
        error=error,
        group_key=item.group_key,
        external_id=item.external_id,
        currency=currency,
        order_id=order_id,
        type_raw=type_raw,
        transaction_type=transaction_type,
        known_type=known_type,
        payout_status=payout_status,
        amount=amount,
        fee=fee,
        net=net,
        posted_at=posted_at,
    )


def _order_id(raw: str) -> str | None:
    text = raw.strip()
    if text == "":
        return None
    return text


def _map_type(raw: str, type_map: dict[str, str]) -> tuple[str, bool]:
    if raw == "":
        raise ValueError("Type 为空。")
    mapped = type_map.get(raw.casefold())
    if mapped is None:
        return raw, False
    return mapped, True


def _check_lengths(
    transaction_type: str,
    type_raw: str,
    order_id: str | None,
    payout_status: str,
) -> None:
    if len(transaction_type) > 64 or len(type_raw) > 64:
        raise ValueError("Type 超过 64 个字符。不能截断。")
    if order_id is not None and len(order_id) > 64:
        raise ValueError("Order 超过 64 个字符。不能截断。")
    if len(f"payout_status={payout_status}") > 512:
        raise ValueError("Payout Status 过长。无法写入结算明细。")


def _groups(
    plans: list[_RowPlan],
    currencies: dict[str, str],
    marketplace: str,
    store_name: str,
) -> tuple[dict[str, _GroupPlan], set[int]]:
    grouped: dict[str, list[_RowPlan]] = defaultdict(list)
    for plan in plans:
        if plan.error is None:
            grouped[plan.group_key].append(plan)
    groups: dict[str, _GroupPlan] = {}
    header_rows: set[int] = set()
    for key, rows in grouped.items():
        external_id = rows[0].external_id
        deposits = {_deposit_at(row.payload.get("Payout Date", "")) for row in rows}
        dated = {item for item in deposits if item is not None}
        if len(dated) > 1:
            raise ValueError(f"结算 {external_id} 有多个 Payout Date。不猜测打款日。")
        posted = [row.posted_at for row in rows if row.posted_at is not None]
        if not posted or any(row.net is None for row in rows):
            raise ValueError(f"结算 {external_id} 缺少可加总的净额或交易时间。")
        total = Decimal("0")
        for row in rows:
            assert row.net is not None
            total += row.net
        first = min(row.row_no for row in rows)
        header_rows.add(first)
        groups[key] = _GroupPlan(
            external_id=external_id,
            currency=currencies[key],
            total=total,
            period_start=min(posted),
            period_end=max(posted),
            deposit_date=next(iter(dated)) if dated else None,
            marketplace=marketplace,
            store_name=store_name,
        )
    return groups, header_rows


def _header(plan: _GroupPlan) -> SettlementHeader:
    return SettlementHeader(
        platform=Platform.SHOPIFY,
        external_id=plan.external_id,
        period_start=plan.period_start,
        period_end=plan.period_end,
        deposit_date=plan.deposit_date,
        total=plan.total,
        currency=plan.currency,
        marketplace=plan.marketplace,
        store_name=plan.store_name,
    )


def _line(plan: _RowPlan) -> SettlementLineRec:
    if plan.net is None or plan.posted_at is None:
        raise ValueError(f"第 {plan.row_no} 行缺少净额或交易时间。")
    return SettlementLineRec(
        platform=Platform.SHOPIFY,
        external_id=plan.external_id,
        transaction_type=plan.transaction_type,
        amount=plan.net,
        order_id=plan.order_id,
        amount_type=plan.type_raw or None,
        amount_description=f"payout_status={plan.payout_status}",
        posted_at=plan.posted_at,
    )


def _mismatch_issue(plan: _RowPlan) -> IssueRec | None:
    if plan.amount is None or plan.fee is None or plan.net is None:
        return None
    expected = plan.amount - plan.fee
    if plan.net == expected:
        return None
    diff = plan.net - expected
    return IssueRec(
        issue_kind=IssueKind.AMOUNT_MISMATCH,
        severity="error",
        detail_json={
            "row_no": plan.row_no,
            "order_id": plan.order_id,
            "amount": _decimal_text(plan.amount),
            "fee": _decimal_text(plan.fee),
            "net": _decimal_text(plan.net),
            "expected_net": _decimal_text(expected),
            "diff": _decimal_text(diff),
        },
    )


def _unknown_type_issue(plan: _RowPlan) -> IssueRec:
    return IssueRec(
        issue_kind=IssueKind.UNKNOWN_FEE_TYPE,
        severity="warn",
        detail_json={
            "row_no": plan.row_no,
            "order_id": plan.order_id,
            "transaction_type": plan.transaction_type,
            "amount_type": plan.type_raw,
            "amount_description": plan.type_raw,
        },
    )


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _parse_money(text: str, currency: str, forced_locale: Locale | None) -> Decimal:
    try:
        return parse_amount(text, _amount_locale(text, currency, forced_locale))
    except AmountParseError as exc:
        raise ValueError(f"无法解析金额 {text!r}。") from exc


def _amount_locale(text: str, currency: str, forced_locale: Locale | None) -> Locale:
    if forced_locale is not None:
        return forced_locale
    body = text.strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1].strip()
    if body[:1] in "+-":
        body = body[1:].strip()
    # 出现逗号小数时按币种选 locale。USD 仍是 us。待真实数据验证。
    if "," in body and body.rfind(",") > body.rfind("."):
        return locale_for(None, currency)
    return "us"


def _parse_transaction_date(text: str) -> datetime:
    body = text.strip()
    if body == "":
        raise ValueError("Transaction Date 为空。")
    parsed = _parse_zoned(body, _TXN_FORMATS)
    if parsed is None:
        raise ValueError(f"无法解析 Transaction Date {text!r}。需要带时区。待真实数据验证。")
    return parsed


def _parse_payout_date(text: str) -> datetime | None:
    body = text.strip()
    if body == "":
        return None
    for fmt in _PAYOUT_FORMATS:
        try:
            parsed = datetime.strptime(body, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            # 只有日期。推断为 UTC 零点。待真实数据验证。
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    raise ValueError(f"无法解析 Payout Date {text!r}。待真实数据验证。")


def _deposit_at(text: str) -> datetime | None:
    return _parse_payout_date(text)


def _parse_zoned(text: str, formats: tuple[str, ...]) -> datetime | None:
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            continue
        return parsed.astimezone(UTC)
    return None
