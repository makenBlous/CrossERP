"""通用映射导入。列名只来自 YAML。sniff 恒为 0。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from crosserp.connectors.base import SourceKind
from crosserp.connectors.generic_mapped.mapping import (
    MappingError,
    MappingSpec,
    coerce_mapping,
    field_text,
    missing_header_message,
    missing_headers,
    require_text,
    timezone_for_name,
)
from crosserp.connectors.generic_mapped.periods import (
    overlap_message,
    periods_overlap,
    segment_text,
)
from crosserp.connectors.generic_mapped.reader import Table, read_table
from crosserp.core.enums import Platform
from crosserp.core.models import (
    CanonicalRecord,
    ColumnMapping,
    FeeReferenceRec,
    FxRateRec,
    OrderLineRec,
    RawRow,
    SkuCostRec,
    SkuRec,
)
from crosserp.core.money import parse_amount

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_MONEY_QUANTUM = Decimal("0.0001")
_FX_QUANTUM = Decimal("0.00000001")

# 合成样本店名。推断。不是平台字段全集。
# 真实导出请在 YAML 里写 platform、marketplace、store_currency。
_STORE_HINTS: dict[str, tuple[Platform, str, str]] = {
    "amazon-us": (Platform.AMAZON, "Amazon.com", "USD"),
    "amazon-de": (Platform.AMAZON, "Amazon.de", "EUR"),
    "shopify-main": (Platform.SHOPIFY, "shopify", "USD"),
}


@dataclass
class _CostDraft:
    row_no: int
    sku: str
    valid_from: datetime
    valid_to: datetime | None
    explicit_end: bool
    error: str | None = None


@dataclass
class _Prepared:
    error: str | None = None
    valid_to: datetime | None = None


class GenericMappedConnector:
    """把任意 csv/xlsx 按 YAML 收成订单、成本、汇率或 SKU 映射。"""

    id = "generic.mapped"
    # SourceKind 没有 generic。真正写入哪张表由 YAML target 决定。sniff 恒为 0。
    kind: SourceKind = "orders"
    version = "0.1.0"

    def __init__(self) -> None:
        self._spec: MappingSpec | None = None
        self._prepared: dict[int, _Prepared] = {}

    def sniff(self, path: Path) -> float:
        """不自动识别。必须显式指定 mapped 和映射文件。"""
        del path
        return 0.0

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        """先整表校验表头。再逐行给出原始字符串。"""
        spec = coerce_mapping(mapping)
        table = read_table(path, spec)
        missing = missing_headers(spec, table.headers)
        if missing:
            raise MappingError(missing_header_message(missing, table.headers))
        self._spec = spec
        self._prepared = _prepare(spec, table)
        for row_no, payload in table.rows:
            yield RawRow(row_no=row_no, payload=payload, source_file=path.name)

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        """把一行变成标准记录。重叠成本在这里报错。导入器写成 PARSE_ERROR。"""
        spec = self._spec
        if spec is None:
            raise ValueError("还没有读取文件。不能标准化。")
        prepared = self._prepared.get(row.row_no)
        if prepared is not None and prepared.error is not None:
            raise ValueError(prepared.error)
        if spec.target == "order_line":
            return [_order(spec, row)]
        if spec.target == "sku_cost":
            return [_cost(spec, row, prepared)]
        if spec.target == "fx_rate":
            return [_fx(spec, row)]
        if spec.target == "fee_reference":
            return [_fee_reference(spec, row)]
        return [_sku(spec, row)]


def _prepare(spec: MappingSpec, table: Table) -> dict[int, _Prepared]:
    if spec.target != "sku_cost":
        return {}
    drafts: list[_CostDraft] = []
    prepared: dict[int, _Prepared] = {}
    for row_no, payload in table.rows:
        try:
            drafts.append(_cost_draft(spec, row_no, payload))
        except ValueError as exc:
            prepared[row_no] = _Prepared(error=str(exc))
    _close_and_flag(drafts)
    for draft in drafts:
        prepared[draft.row_no] = _Prepared(error=draft.error, valid_to=draft.valid_to)
    return prepared


def _cost_draft(spec: MappingSpec, row_no: int, payload: dict[str, str]) -> _CostDraft:
    sku = require_text(spec, payload, "internal_sku")
    start = _parse_datetime(require_text(spec, payload, "valid_from"), spec)
    end_text = field_text(spec, payload, "valid_to")
    end = None if end_text is None else _parse_datetime(end_text, spec)
    if end is not None and end <= start:
        raise ValueError(f"第 {row_no} 行结束时间必须晚于生效时间。")
    return _CostDraft(
        row_no=row_no,
        sku=sku,
        valid_from=start,
        valid_to=end,
        explicit_end=end is not None,
    )


def _close_and_flag(drafts: list[_CostDraft]) -> None:
    """未填结束日时接到同一 SKU 的下一条生效日。不含下一条当天。推断。与样本生成器一致。"""
    grouped: dict[str, list[_CostDraft]] = {}
    for draft in drafts:
        grouped.setdefault(draft.sku, []).append(draft)
    for sku, group in grouped.items():
        group.sort(key=lambda item: (item.valid_from, item.row_no))
        for index, item in enumerate(group):
            if item.explicit_end or index + 1 >= len(group):
                continue
            nxt = group[index + 1]
            if nxt.valid_from > item.valid_from:
                item.valid_to = nxt.valid_from
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if not periods_overlap(
                    left.valid_from, left.valid_to, right.valid_from, right.valid_to
                ):
                    continue
                message = overlap_message(
                    sku,
                    f"第 {left.row_no} 行 {segment_text(left.valid_from, left.valid_to)}",
                    f"第 {right.row_no} 行 {segment_text(right.valid_from, right.valid_to)}",
                )
                left.error = message
                right.error = message


def _order(spec: MappingSpec, row: RawRow) -> OrderLineRec:
    store = _store(spec, row.payload, currency_field="currency")
    price_text = field_text(spec, row.payload, "item_price")
    item_id = field_text(spec, row.payload, "order_item_id")
    return OrderLineRec(
        platform=store.platform,
        marketplace=store.marketplace,
        store_name=store.name,
        store_currency=store.currency,
        platform_order_id=_limit(
            require_text(spec, row.payload, "platform_order_id"), 64, "订单号"
        ),
        order_item_id=None if item_id is None else _limit(item_id, 64, "订单项"),
        platform_sku=_limit(require_text(spec, row.payload, "platform_sku"), 128, "平台 SKU"),
        qty=_parse_qty(require_text(spec, row.payload, "qty")),
        order_date=_parse_datetime(require_text(spec, row.payload, "order_date"), spec),
        item_price=None if price_text is None else _parse_money(price_text, spec),
        currency=_currency(require_text(spec, row.payload, "currency")),
    )


def _cost(spec: MappingSpec, row: RawRow, prepared: _Prepared | None) -> SkuCostRec:
    if prepared is None:
        raise ValueError(f"第 {row.row_no} 行没有成本预计算。")
    return SkuCostRec(
        internal_sku=_limit(require_text(spec, row.payload, "internal_sku"), 64, "内部 SKU"),
        valid_from=_parse_datetime(require_text(spec, row.payload, "valid_from"), spec),
        valid_to=prepared.valid_to,
        unit_cost=_parse_money(require_text(spec, row.payload, "unit_cost"), spec),
        currency=_currency(require_text(spec, row.payload, "currency")),
        freight_per_unit=_parse_money(require_text(spec, row.payload, "freight_per_unit"), spec),
    )


def _fx(spec: MappingSpec, row: RawRow) -> FxRateRec:
    source = field_text(spec, row.payload, "source") or spec.source_name
    return FxRateRec(
        period=_period(require_text(spec, row.payload, "period")),
        from_ccy=_currency(require_text(spec, row.payload, "from_ccy")),
        to_ccy=_currency(require_text(spec, row.payload, "to_ccy")),
        rate=_parse_rate(require_text(spec, row.payload, "rate"), spec),
        source=_limit(source, 128, "汇率来源"),
    )


def _fee_reference(spec: MappingSpec, row: RawRow) -> FeeReferenceRec:
    valid_to = field_text(spec, row.payload, "valid_to")
    fee_category = require_text(spec, row.payload, "fee_category").strip().casefold()
    return FeeReferenceRec(
        internal_sku=_limit(require_text(spec, row.payload, "internal_sku"), 128, "内部 SKU"),
        fee_category=_limit(fee_category, 32, "费用类别"),
        currency=_currency(require_text(spec, row.payload, "currency")),
        expected_per_unit=_parse_money(require_text(spec, row.payload, "expected_per_unit"), spec),
        valid_from=_parse_datetime(require_text(spec, row.payload, "valid_from"), spec),
        valid_to=None if valid_to is None else _parse_datetime(valid_to, spec),
    )


def _sku(spec: MappingSpec, row: RawRow) -> SkuRec:
    store = _store(spec, row.payload, currency_field=None)
    title = field_text(spec, row.payload, "title")
    active_text = field_text(spec, row.payload, "active")
    return SkuRec(
        platform=store.platform,
        marketplace=store.marketplace,
        store_name=store.name,
        store_currency=store.currency,
        platform_sku=_limit(require_text(spec, row.payload, "platform_sku"), 128, "平台 SKU"),
        internal_sku=_limit(require_text(spec, row.payload, "internal_sku"), 128, "内部 SKU"),
        title=None if title is None else _limit(title, 512, "标题"),
        active=True if active_text is None else _parse_active(active_text),
    )


@dataclass(frozen=True)
class _Store:
    platform: Platform
    marketplace: str
    name: str
    currency: str


def _store(spec: MappingSpec, payload: dict[str, str], *, currency_field: str | None) -> _Store:
    store_key = require_text(spec, payload, "store")
    hint = _STORE_HINTS.get(store_key)
    platform_text = field_text(spec, payload, "platform")
    if platform_text is None:
        platform = hint[0] if hint is not None else _platform_from_prefix(store_key)
    else:
        platform = _platform(platform_text)
    marketplace = field_text(spec, payload, "marketplace")
    if marketplace is None:
        marketplace = hint[1] if hint is not None else store_key
    name = field_text(spec, payload, "store_name") or store_key
    currency_text = field_text(spec, payload, "store_currency")
    if currency_text is None and currency_field is not None:
        currency_text = field_text(spec, payload, currency_field)
    if currency_text is None and hint is not None:
        currency_text = hint[2]
    if currency_text is None:
        raise ValueError(
            f"无法确定店铺 {store_key} 的币种。请在 YAML defaults 里填写 store_currency。"
        )
    return _Store(
        platform=platform,
        marketplace=_limit(marketplace, 64, "站点"),
        name=_limit(name, 255, "店铺名"),
        currency=_currency(currency_text),
    )


def _platform(text: str) -> Platform:
    try:
        return Platform(text.strip().casefold())
    except ValueError as exc:
        allowed = "、".join(item.value for item in Platform)
        raise ValueError(f"不认识的平台 {text!r}。允许 {allowed}。不会猜测。") from exc


def _platform_from_prefix(store_key: str) -> Platform:
    """店名没有 defaults.platform 时的前缀。推断。不是平台字段全集。"""
    lowered = store_key.casefold()
    if lowered.startswith("amazon"):
        return Platform.AMAZON
    if lowered.startswith("shopify"):
        return Platform.SHOPIFY
    if lowered.startswith("lingxing") or "领星" in store_key:
        return Platform.LINGXING
    if lowered.startswith("sellfox") or "赛狐" in store_key:
        return Platform.SELLFOX
    return Platform.OTHER


def _parse_datetime(text: str, spec: MappingSpec) -> datetime:
    if not spec.timezone or not spec.date_formats:
        raise ValueError("YAML 缺少 timezone 或 date_formats。")
    zone = timezone_for_name(spec.timezone)
    for fmt in spec.date_formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            parsed = parsed.replace(tzinfo=zone)
        return parsed.astimezone(UTC)
    shown = "、".join(spec.date_formats)
    raise ValueError(f"时间无法按 {shown} 解析 {text!r}。")


def _parse_money(text: str, spec: MappingSpec) -> Decimal:
    if spec.amount_locale is None:
        raise ValueError("YAML 缺少 amount_locale。")
    amount = parse_amount(text, spec.amount_locale)
    _reject_places(amount, _MONEY_QUANTUM, f"金额小数位超过 4 位。拒绝舍入 {text!r}")
    return amount


def _parse_rate(text: str, spec: MappingSpec) -> Decimal:
    if spec.amount_locale is None:
        raise ValueError("YAML 缺少 amount_locale。")
    rate = parse_amount(text, spec.amount_locale)
    _reject_places(rate, _FX_QUANTUM, f"汇率小数位超过 8 位。拒绝舍入 {text!r}")
    return rate


def _reject_places(value: Decimal, quantum: Decimal, message: str) -> None:
    try:
        quantized = value.quantize(quantum)
    except InvalidOperation as exc:
        raise ValueError(message) from exc
    if quantized != value:
        raise ValueError(message)


def _parse_qty(text: str) -> int:
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"数量无法解析 {text!r}") from exc
    if not number.is_finite() or number != number.to_integral_value() or number < 0:
        raise ValueError(f"数量必须是非负整数 {text!r}")
    return int(number)


def _parse_active(text: str) -> bool:
    body = text.casefold()
    if body in {"1", "true", "yes", "y"}:
        return True
    if body in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"active 无法解析 {text!r}。只接受 true/false/1/0。")


def _currency(text: str) -> str:
    code = text.strip().upper()
    if _CURRENCY_RE.fullmatch(code) is None:
        raise ValueError(f"币种必须是 3 位字母 {text!r}")
    return code


def _period(text: str) -> str:
    if _PERIOD_RE.fullmatch(text) is None:
        raise ValueError(f"月份必须是 YYYY-MM {text!r}")
    return text


def _limit(text: str, max_length: int, label: str) -> str:
    if len(text) > max_length:
        raise ValueError(f"{label} 超过 {max_length} 个字符。")
    return text
