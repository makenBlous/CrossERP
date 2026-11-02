"""Amazon Settlement Flat File V2。按表头名取列。不写数据库。"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from crosserp.connectors.amazon_settlement_v2.dates import parse_amazon_date
from crosserp.connectors.base import SourceKind
from crosserp.core.enums import FeeCategory, IssueKind, Platform
from crosserp.core.errors import AmountParseError
from crosserp.core.models import (
    CanonicalRecord,
    ColumnMapping,
    IssueRec,
    RawRow,
    SettlementHeader,
    SettlementLineRec,
)
from crosserp.core.money import locale_for, parse_amount

# 官方 24 列。列名已核实。取值不是全集。
_OFFICIAL = frozenset(
    {
        "settlement-id",
        "settlement-start-date",
        "settlement-end-date",
        "deposit-date",
        "total-amount",
        "currency",
        "transaction-type",
        "order-id",
        "merchant-order-id",
        "adjustment-id",
        "shipment-id",
        "marketplace-name",
        "amount-type",
        "amount-description",
        "amount",
        "fulfillment-id",
        "posted-date",
        "posted-date-time",
        "order-item-code",
        "merchant-order-item-id",
        "merchant-adjustment-item-id",
        "sku",
        "quantity-purchased",
        "promotion-id",
    }
)
_REQUIRED = (
    "settlement-id",
    "total-amount",
    "currency",
    "transaction-type",
    "amount-type",
    "amount-description",
    "amount",
)
_SNIFF = frozenset({"settlement-id", "amount-type", "amount-description", "total-amount"})
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_QTY_RE = re.compile(r"[+-]?\d+")
# 无表头的多余字段。不是平台列名。只用来不丢数据。
_EXTRA = "_extra"
_FEE_MAP: dict[tuple[str, str], FeeCategory] | None = None

Role = Literal["summary", "line", "duplicate", "invalid"]


class MissingColumnsError(Exception):
    """缺少必需列。整批失败。不要当成单行 PARSE_ERROR。"""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(f"缺少必需列 {'、'.join(missing)}")


class DuplicateHeaderError(Exception):
    """表头列名重复。按表头名取列会丢值。整批失败。"""

    def __init__(self, names: tuple[str, ...]) -> None:
        self.names = names
        super().__init__(f"表头列名重复 {'、'.join(names)}")


@dataclass(frozen=True)
class _Classified:
    row: RawRow
    role: Role
    duplicate_of: int | None = None
    reason: str | None = None


class AmazonSettlementV2Connector:
    """读 Flat File V2。汇总行不参与交易求和。"""

    id = "amazon.settlement_v2"
    kind: SourceKind = "settlement"
    version = "0.1.0"

    def __init__(self) -> None:
        self._plans: dict[int, list[CanonicalRecord]] = {}

    def sniff(self, path: Path) -> float:
        """首行按 tab 分割。四个关键列都在则 0.95。否则 0。"""
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header = handle.readline()
        except (OSError, UnicodeError):
            return 0.0
        names = {part.strip() for part in header.split("\t")}
        if names >= _SNIFF:
            return 0.95
        return 0.0

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        """按表头名读行。缺必需列时整批失败。"""
        del mapping
        self._plans = {}
        rows, unknown = _load_rows(path)
        plans = _plan(rows, unknown)
        self._plans = plans
        yield from _headers_first(rows, plans)

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        """返回 read 时算好的标准记录。同一行重复调用结果相同。"""
        planned = self._plans.get(row.row_no)
        if planned is None:
            raise ValueError(f"第 {row.row_no} 行没有解析结果。请先读取文件。")
        return list(planned)


def load_fee_map() -> dict[tuple[str, str], FeeCategory]:
    """读取 fee_map.yaml。未知组合不在表里。调用方不要猜。"""
    global _FEE_MAP
    if _FEE_MAP is not None:
        return _FEE_MAP
    path = Path(__file__).with_name("fee_map.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("fee_map.yaml 必须是映射")
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        raise ValueError("fee_map.yaml 缺少 entries")
    mapping: dict[tuple[str, str], FeeCategory] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("fee_map.yaml 的条目必须是映射")
        amount_type = item.get("amount_type")
        amount_description = item.get("amount_description")
        category = item.get("fee_category")
        if not isinstance(amount_type, str) or not isinstance(amount_description, str):
            raise ValueError("fee_map.yaml 的费用名必须是字符串")
        if not isinstance(category, str):
            raise ValueError(f"fee_map.yaml 费用分类无法识别 {category!r}")
        try:
            parsed = FeeCategory(category)
        except ValueError as exc:
            raise ValueError(f"fee_map.yaml 费用分类无法识别 {category!r}") from exc
        mapping[(amount_type, amount_description)] = parsed
    _FEE_MAP = mapping
    return mapping


def _load_rows(path: Path) -> tuple[list[RawRow], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", restkey=_EXTRA, restval="")
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise MissingColumnsError(_REQUIRED)
        cleaned, duplicates = _clean_headers(fieldnames)
        if duplicates:
            raise DuplicateHeaderError(tuple(duplicates))
        present = set(cleaned)
        missing = tuple(name for name in _REQUIRED if name not in present)
        if missing:
            raise MissingColumnsError(missing)
        unknown = [name for name in cleaned if name not in _OFFICIAL]
        rows: list[RawRow] = []
        seen_extra = False
        for raw in reader:
            payload = _payload(raw)
            if _EXTRA in payload:
                seen_extra = True
            if payload and any(value != "" for value in payload.values()):
                rows.append(RawRow(row_no=reader.line_num, payload=payload, source_file=path.name))
        if seen_extra and _EXTRA not in unknown:
            unknown.append(_EXTRA)
        return rows, unknown


def _clean_headers(fieldnames: Sequence[str]) -> tuple[list[str], list[str]]:
    cleaned: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in fieldnames:
        text = name.strip()
        if text in seen and text not in duplicates:
            duplicates.append(text)
        seen.add(text)
        cleaned.append(text)
    return cleaned, duplicates


def _payload(raw: Mapping[str, object]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for key, value in raw.items():
        if key == _EXTRA:
            payload[_EXTRA] = _extra_text(value)
            continue
        payload[key.strip()] = "" if not isinstance(value, str) else value
    return payload


def _extra_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [item for item in value if isinstance(item, str)]
        return "\t".join(parts)
    return ""


def _plan(rows: list[RawRow], unknown: list[str]) -> dict[int, list[CanonicalRecord]]:
    classified = [_classify(row, _identities(rows)) for row in rows]
    headers, _header_rows = _headers(classified)
    plans: dict[int, list[CanonicalRecord]] = {}
    for item in classified:
        plans[item.row.row_no] = _records_for(item, headers)
    _attach_balance(plans, classified, headers)
    _attach_unknown(plans, rows, unknown)
    return plans


def _identities(rows: list[RawRow]) -> dict[tuple[tuple[str, str], ...], int]:
    found: dict[tuple[tuple[str, str], ...], int] = {}
    for row in rows:
        key = tuple(sorted(row.payload.items()))
        if key not in found:
            found[key] = row.row_no
    return found


def _classify(row: RawRow, identities: dict[tuple[tuple[str, str], ...], int]) -> _Classified:
    key = tuple(sorted(row.payload.items()))
    first = identities[key]
    if first != row.row_no:
        return _Classified(row, "duplicate", duplicate_of=first)
    transaction_type = _text(row.payload, "transaction-type")
    total_amount = _text(row.payload, "total-amount")
    # 汇总行是 transaction-type 为空且 total-amount 非空。推断。待真实数据验证。
    if transaction_type == "" and total_amount != "":
        return _Classified(row, "summary")
    if transaction_type == "":
        return _Classified(
            row,
            "invalid",
            reason="transaction-type 与 total-amount 都为空。无法判断行类型。",
        )
    return _Classified(row, "line")


def _headers(
    classified: list[_Classified],
) -> tuple[dict[str, SettlementHeader], dict[str, int]]:
    owners: dict[str, int] = {}
    conflicts: set[str] = set()
    for item in classified:
        if item.role != "summary":
            continue
        external_id = _text(item.row.payload, "settlement-id")
        if external_id == "":
            continue
        if external_id in owners:
            conflicts.add(external_id)
        else:
            owners[external_id] = item.row.row_no
    headers: dict[str, SettlementHeader] = {}
    header_rows: dict[str, int] = {}
    for item in classified:
        if item.role != "summary":
            continue
        external_id = _text(item.row.payload, "settlement-id")
        if external_id == "" or external_id in conflicts:
            continue
        if owners.get(external_id) != item.row.row_no:
            continue
        try:
            headers[external_id] = _build_header(item.row)
        except (AmountParseError, ValidationError, ValueError):
            continue
        header_rows[external_id] = item.row.row_no
    return headers, header_rows


def _line_sums(
    classified: list[_Classified],
    headers: dict[str, SettlementHeader],
) -> tuple[dict[str, Decimal], dict[str, bool]]:
    sums = {external_id: Decimal("0") for external_id in headers}
    ok = {external_id: True for external_id in headers}
    for item in classified:
        if not _counts_toward_total(item):
            continue
        external_id = _text(item.row.payload, "settlement-id")
        header = headers.get(external_id)
        if header is None:
            continue
        try:
            # 重复交易行仍计入总额。文件总额含这两行。汇总行的重复不算交易。
            sums[external_id] += _line_amount(item.row, header.currency)
        except (AmountParseError, ValueError):
            # 有行算不出金额时差额不可靠。不把解析失败再报成不平。
            ok[external_id] = False
    return sums, ok


def _counts_toward_total(item: _Classified) -> bool:
    if item.role == "line":
        return True
    if item.role != "duplicate":
        return False
    return _text(item.row.payload, "transaction-type") != ""


def _records_for(item: _Classified, headers: dict[str, SettlementHeader]) -> list[CanonicalRecord]:
    row_no = item.row.row_no
    if item.role == "duplicate":
        first = item.duplicate_of if item.duplicate_of is not None else row_no
        return [_issue(IssueKind.DUPLICATE_ROW, "warn", {"row_no": row_no, "first_row_no": first})]
    if item.role == "invalid":
        return [
            _issue(
                IssueKind.PARSE_ERROR,
                "error",
                {"row_no": row_no, "error": item.reason or "无法解析"},
            )
        ]
    if item.role == "summary":
        return _summary_records(item.row, headers)
    return _line_records(item.row, headers)


def _summary_records(row: RawRow, headers: dict[str, SettlementHeader]) -> list[CanonicalRecord]:
    external_id = _text(row.payload, "settlement-id")
    header = headers.get(external_id)
    if header is None:
        reason = _summary_failure_reason(row)
        return [_issue(IssueKind.PARSE_ERROR, "error", {"row_no": row.row_no, "error": reason})]
    return [header]


def _summary_failure_reason(row: RawRow) -> str:
    external_id = _text(row.payload, "settlement-id")
    if external_id == "":
        return "汇总行缺少 settlement-id"
    try:
        _build_header(row)
    except (AmountParseError, ValidationError, ValueError) as exc:
        return _error_text(exc)
    return "同一 settlement-id 有多条不一致的汇总行。不猜用哪一条。"


def _line_records(row: RawRow, headers: dict[str, SettlementHeader]) -> list[CanonicalRecord]:
    external_id = _text(row.payload, "settlement-id")
    header = headers.get(external_id)
    if header is None:
        return [
            _issue(
                IssueKind.PARSE_ERROR,
                "error",
                {"row_no": row.row_no, "error": f"结算明细缺少可用的汇总行 {external_id}"},
            )
        ]
    try:
        line = _build_line(row, header.currency)
    except (AmountParseError, ValidationError, ValueError) as exc:
        return [
            _issue(
                IssueKind.PARSE_ERROR, "error", {"row_no": row.row_no, "error": _error_text(exc)}
            )
        ]
    records: list[CanonicalRecord] = [line]
    amount_type = _text(row.payload, "amount-type")
    amount_description = _text(row.payload, "amount-description")
    if (amount_type, amount_description) not in load_fee_map():
        records.append(
            _issue(
                IssueKind.UNKNOWN_FEE_TYPE,
                "warn",
                {
                    "row_no": row.row_no,
                    "amount_type": amount_type,
                    "amount_description": amount_description,
                },
            )
        )
    return records


def _attach_balance(
    plans: dict[int, list[CanonicalRecord]],
    classified: list[_Classified],
    headers: dict[str, SettlementHeader],
) -> None:
    sums, ok = _line_sums(classified, headers)
    for item in classified:
        if item.role != "summary":
            continue
        external_id = _text(item.row.payload, "settlement-id")
        header = headers.get(external_id)
        if header is None or not ok.get(external_id, False):
            continue
        line_sum = sums[external_id]
        if line_sum == header.total:
            continue
        diff = line_sum - header.total
        plans[item.row.row_no].append(
            _issue(
                IssueKind.SETTLEMENT_UNBALANCED,
                "error",
                {
                    "row_no": item.row.row_no,
                    "settlement_id": external_id,
                    "total_amount": _decimal_text(header.total),
                    "line_sum": _decimal_text(line_sum),
                    "diff": _decimal_text(diff),
                },
            )
        )


def _attach_unknown(
    plans: dict[int, list[CanonicalRecord]],
    rows: list[RawRow],
    unknown: list[str],
) -> None:
    if not unknown or not rows:
        return
    first = min(row.row_no for row in rows)
    plans[first].append(
        _issue(
            IssueKind.PARSE_ERROR,
            "info",
            {
                "row_no": first,
                "error": "未知列已保留",
                "columns": unknown,
            },
        )
    )


def _headers_first(rows: list[RawRow], plans: dict[int, list[CanonicalRecord]]) -> list[RawRow]:
    headers: list[RawRow] = []
    rest: list[RawRow] = []
    for row in rows:
        records = plans[row.row_no]
        if any(isinstance(record, SettlementHeader) for record in records):
            headers.append(row)
        else:
            rest.append(row)
    return [*headers, *rest]


def _build_header(row: RawRow) -> SettlementHeader:
    payload = row.payload
    external_id = _text(payload, "settlement-id")
    if external_id == "":
        raise ValueError("汇总行缺少 settlement-id")
    currency = _currency(payload)
    marketplace = _text(payload, "marketplace-name")
    if marketplace == "":
        raise ValueError("汇总行缺少 marketplace-name")
    total = parse_amount(_text(payload, "total-amount"), locale_for(marketplace, currency))
    period_start = _required_date(payload, "settlement-start-date")
    period_end = _required_date(payload, "settlement-end-date")
    deposit_date = parse_amazon_date(_text(payload, "deposit-date"))
    # 店名没有单独列。用 marketplace-name。推断。待真实数据验证。
    return SettlementHeader(
        platform=Platform.AMAZON,
        external_id=external_id,
        period_start=period_start,
        period_end=period_end,
        deposit_date=deposit_date,
        total=total,
        currency=currency,
        marketplace=marketplace,
        store_name=marketplace,
    )


def _build_line(row: RawRow, header_currency: str) -> SettlementLineRec:
    payload = row.payload
    external_id = _text(payload, "settlement-id")
    if external_id == "":
        raise ValueError("结算明细缺少 settlement-id")
    currency = _currency(payload)
    if currency != header_currency:
        raise ValueError(f"明细币种 {currency} 与汇总行 {header_currency} 不一致")
    transaction_type = _text(payload, "transaction-type")
    if transaction_type == "":
        raise ValueError("交易行缺少 transaction-type")
    amount = _line_amount(row, header_currency)
    amount_type = _text(payload, "amount-type")
    amount_description = _text(payload, "amount-description")
    category = load_fee_map().get((amount_type, amount_description), FeeCategory.OTHER)
    return SettlementLineRec(
        platform=Platform.AMAZON,
        external_id=external_id,
        transaction_type=transaction_type,
        amount=amount,
        order_id=_or_none(_text(payload, "order-id")),
        order_item_code=_or_none(_text(payload, "order-item-code")),
        sku=_or_none(_text(payload, "sku")),
        qty=_qty(payload),
        amount_type=_or_none(amount_type),
        amount_description=_or_none(amount_description),
        posted_at=_posted_at(payload),
        fee_category=category,
    )


def _line_amount(row: RawRow, header_currency: str) -> Decimal:
    payload = row.payload
    currency = _currency(payload)
    if currency != header_currency:
        raise ValueError(f"明细币种 {currency} 与汇总行 {header_currency} 不一致")
    marketplace = _text(payload, "marketplace-name") or None
    return parse_amount(_text(payload, "amount"), locale_for(marketplace, currency))


def _posted_at(payload: dict[str, str]) -> datetime | None:
    # 优先 posted-date-time。推断。待真实数据验证。失败时不改用另一列。
    posted = _text(payload, "posted-date-time")
    if posted == "":
        posted = _text(payload, "posted-date")
    if posted == "":
        return None
    return parse_amazon_date(posted)


def _required_date(payload: dict[str, str], key: str) -> datetime:
    text = _text(payload, key)
    if text == "":
        raise ValueError(f"汇总行缺少 {key}")
    parsed = parse_amazon_date(text)
    if parsed is None:
        raise ValueError(f"汇总行缺少 {key}")
    return parsed


def _currency(payload: dict[str, str]) -> str:
    currency = _text(payload, "currency")
    if _CURRENCY_RE.fullmatch(currency) is None:
        raise ValueError(f"币种无法识别 {currency!r}")
    return currency


def _qty(payload: dict[str, str]) -> int | None:
    text = _text(payload, "quantity-purchased")
    if text == "":
        return None
    if _QTY_RE.fullmatch(text) is None:
        raise ValueError(f"数量无法解析 {text!r}")
    return int(text)


def _text(payload: dict[str, str], key: str) -> str:
    return payload.get(key, "").strip()


def _or_none(value: str) -> str | None:
    if value == "":
        return None
    return value


def _issue(kind: IssueKind, severity: str, detail: dict[str, object]) -> IssueRec:
    return IssueRec(issue_kind=kind, severity=severity, detail_json=detail)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "字段长度或格式不符合结算记录"
    return str(exc)


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")
