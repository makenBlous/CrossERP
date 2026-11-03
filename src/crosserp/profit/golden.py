"""Compare persisted profit snapshots with an explicit CSV golden file."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Issue, ProfitSnapshot, Store


@dataclass(frozen=True)
class GoldenDiff:
    key: str
    column: str
    expected: str
    actual: str


@dataclass(frozen=True)
class GoldenResult:
    expected_rows: int
    compared_rows: int
    matched_rows: int
    reference_only_rows: int
    missing_rows: tuple[str, ...]
    diffs: tuple[GoldenDiff, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_rows and not self.diffs


@dataclass(frozen=True)
class IssueGoldenResult:
    expected: int
    matched: int
    missing: tuple[str, ...]
    extra: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing and not self.extra


_MONEY_COLUMNS = (
    "revenue",
    "promotion",
    "platform_fees",
    "refunds",
    "cogs",
    "freight",
    "profit",
    "profit_cny",
)
_INT_COLUMNS = ("qty_sold", "qty_refunded")


def _display(value: object, *, money: bool = False) -> str:
    if value is None:
        return ""
    if money:
        return f"{Decimal(str(value)).quantize(Decimal('0.01')):.2f}"
    return str(value)


def compare_profit_csv(
    session: Session, period: str, path: Path, store_name: str | None = None
) -> GoldenResult:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    statement = (
        select(ProfitSnapshot, Store)
        .join(Store, Store.id == ProfitSnapshot.store_id)
        .where(ProfitSnapshot.period == period)
    )
    if store_name is not None:
        statement = statement.where(Store.name == store_name)
    actual = {
        (store.name, snapshot.internal_sku): snapshot
        for snapshot, store in session.execute(statement)
    }
    missing: list[str] = []
    diffs: list[GoldenDiff] = []
    compared = 0
    matched = 0
    reference_only = 0
    for row in rows:
        key = f"{row.get('store', '')}:{row.get('internal_sku', '')}"
        if row.get("note", "").startswith("reference-only"):
            reference_only += 1
            continue
        compared += 1
        snapshot = actual.get((row.get("store", ""), row.get("internal_sku", "")))
        if snapshot is None:
            missing.append(key)
            continue
        row_diffs: list[GoldenDiff] = []
        for column in _INT_COLUMNS:
            expected = row.get(column, "")
            value = _display(getattr(snapshot, column), money=False)
            if expected != value:
                row_diffs.append(GoldenDiff(key, column, expected, value))
        for column in _MONEY_COLUMNS:
            expected = row.get(column, "")
            if expected in {"", "n/a"}:
                continue
            actual_column = "fees" if column == "platform_fees" else column
            value = _display(getattr(snapshot, actual_column), money=True)
            if expected != value:
                row_diffs.append(GoldenDiff(key, column, expected, value))
        if row_diffs:
            diffs.extend(row_diffs)
        else:
            matched += 1
    return GoldenResult(len(rows), compared, matched, reference_only, tuple(missing), tuple(diffs))


def compare_issues_csv(session: Session, path: Path) -> IssueGoldenResult:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    expected = {
        f"{row.get('order_id', '')}:{row.get('sku', '')}:{row.get('expected_kind', '')}"
        for row in rows
    }
    expected_kinds = {row.get("expected_kind", "") for row in rows}
    actual = set()
    for issue in session.scalars(select(Issue)):
        if issue.kind not in expected_kinds:
            continue
        detail = issue.detail_json if isinstance(issue.detail_json, dict) else {}
        actual.add(f"{detail.get('order_id', '')}:{detail.get('sku', '')}:{issue.kind}")
    missing = tuple(sorted(expected - actual))
    extra = tuple(sorted(actual - expected))
    return IssueGoldenResult(len(expected), len(expected & actual), missing, extra)
