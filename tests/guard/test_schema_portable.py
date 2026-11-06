"""表结构必须三库可移植。不连接数据库。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Text, TypeDecorator

from crosserp.approval.state import ApprovalState
from crosserp.core.enums import (
    FeeCategory,
    ImportStatus,
    IssueKind,
    IssueStatus,
    MatchStatus,
    Platform,
)
from crosserp.db.schema import Base
from crosserp.db.types import FxRate, Money4

pytestmark = pytest.mark.guard

_MONEY_HINT = re.compile(r"amount|total|price|cost|fee|profit|revenue", re.IGNORECASE)
# 实施方案第 4 节的分类字段。名字里带 amount/fee。但不是金额。
_NOT_MONEY = frozenset(
    {
        "amount_type",
        "amount_description",
        "fee_category",
        "groups_total",
        "groups_matched",
        # eval_run.total/passed 是评测题数量, 不是金额。
        "total",
        "passed",
    }
)
_MONEY_COLUMNS = {
    ("sku_cost", "unit_cost"),
    ("sku_cost", "freight_per_unit"),
    ("order_line", "item_price"),
    ("settlement", "total"),
    ("settlement_line", "amount"),
    ("fee", "amount"),
    ("fee_reference", "expected_per_unit"),
    ("match", "diff"),
    ("profit_snapshot", "revenue"),
    ("profit_snapshot", "fees"),
    ("profit_snapshot", "refunds"),
    ("profit_snapshot", "cogs"),
    ("profit_snapshot", "freight"),
    ("profit_snapshot", "ads"),
    ("profit_snapshot", "profit"),
}
_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "crosserp"
    / "db"
    / "migrations"
    / "versions"
    / "0001_initial.py"
)
_FORBIDDEN_MIGRATION = (
    "sqlalchemy.dialects",
    "JSONB",
    "ARRAY",
    "Identity(",
    "DATETIME",
    "TIMESTAMP",
)


def _walk_types(type_: TypeEngine[object]) -> list[TypeEngine[object]]:
    found = [type_]
    if isinstance(type_, TypeDecorator):
        found.extend(_walk_types(type_.impl))
    return found


def _is_forbidden(type_: TypeEngine[object]) -> bool:
    name = type_.__class__.__name__
    module = type_.__class__.__module__
    if name in {"ARRAY", "JSONB"}:
        return True
    return "postgresql" in module and name in {"ARRAY", "JSONB"}


def _string_length(column: Column[object]) -> int | None:
    type_ = column.type
    if isinstance(type_, String):
        return type_.length
    return None


def _expects_money(name: str) -> bool:
    if name in _NOT_MONEY:
        return False
    return _MONEY_HINT.search(name) is not None


def test_metadata_has_no_array_or_jsonb() -> None:
    forbidden: list[str] = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            for type_ in _walk_types(column.type):
                if _is_forbidden(type_):
                    forbidden.append(f"{table.name}.{column.name}:{type_}")
    assert forbidden == []


def test_strings_have_length() -> None:
    missing: list[str] = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if (
                isinstance(column.type, String)
                and not isinstance(column.type, Text)
                and not column.type.length
            ):
                missing.append(f"{table.name}.{column.name}")
    assert missing == []


def test_string_lengths_fit_mysql_utf8mb4_column_limit() -> None:
    oversized = [
        f"{table.name}.{column.name}={column.type.length}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, String)
        and not isinstance(column.type, Text)
        and column.type.length is not None
        and column.type.length > 16_383
    ]
    assert oversized == []


def test_indexed_strings_fit_mysql_prefix() -> None:
    too_long: list[str] = []
    for table in Base.metadata.tables.values():
        column_groups = [list(index.columns) for index in table.indexes]
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                column_groups.append(list(constraint.columns))
        for columns in column_groups:
            lengths: list[int] = []
            for column in columns:
                length = _string_length(column)
                if length is None:
                    continue
                if length > 255:
                    too_long.append(f"{table.name}.{column.name}={length}")
                lengths.append(length)
            if lengths and sum(lengths) * 4 > 3072:
                too_long.append(f"{table.name} index bytes {sum(lengths) * 4}")
    assert too_long == []


def test_money_named_columns_are_money4() -> None:
    bad: list[str] = []
    seen: set[tuple[str, str]] = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            key = (table.name, column.key)
            if key in _MONEY_COLUMNS or _expects_money(column.key):
                seen.add(key)
                if not isinstance(column.type, Money4):
                    bad.append(f"{table.name}.{column.key}={column.type!r}")
    missing = sorted(f"{table}.{column}" for table, column in _MONEY_COLUMNS - seen)
    assert bad == []
    assert missing == []
    rate = Base.metadata.tables["fx_rate"].c.rate
    assert isinstance(rate.type, FxRate)


def test_enum_values_fit_string32() -> None:
    for enum_cls in (
        Platform,
        ImportStatus,
        FeeCategory,
        IssueKind,
        IssueStatus,
        MatchStatus,
        ApprovalState,
    ):
        for item in enum_cls:
            assert len(item.value) <= 32
    # 实施方案 6.1 的 13 个码, 加上 maken 于 2026-11-02 确认的 5 个码。
    assert len(list(IssueKind)) == 18


def test_initial_migration_is_dialect_neutral() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    found = [token for token in _FORBIDDEN_MIGRATION if token in text]
    assert found == []
