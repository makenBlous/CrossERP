"""合成样本生成器。确定性、行数、平衡和场景覆盖。"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
SCRIPTS = REPO / "scripts"


def _modules():
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import gen_samples
    import sample_vocab

    return gen_samples, sample_vocab


def _generate(tmp_path: Path):
    gen_samples, vocab = _modules()
    out = tmp_path / "synthetic"
    gen_samples.generate(out)
    return out, gen_samples, vocab


def _read_csv(path: Path, delimiter: str = ",") -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xlsx_cells(path: Path) -> list[tuple[object, ...]]:
    workbook = load_workbook(path, data_only=True)
    cells: list[tuple[object, ...]] = []
    for sheet in workbook.worksheets:
        cells.append((sheet.title,))
        for row in sheet.iter_rows(values_only=True):
            cells.append(tuple(row))
    workbook.close()
    return cells


def test_generation_is_deterministic(tmp_path: Path) -> None:
    gen_samples, _vocab = _modules()
    first = tmp_path / "a"
    second = tmp_path / "b"
    gen_samples.generate(first)
    gen_samples.generate(second)
    files_a = sorted(
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    )
    files_b = sorted(
        path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()
    )
    assert files_a == files_b
    assert files_a
    for relative in files_a:
        left = first / relative
        right = second / relative
        if left.suffix == ".xlsx":
            assert _xlsx_cells(left) == _xlsx_cells(right)
        else:
            assert _sha256(left) == _sha256(right)


def test_orders_have_120_data_rows(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    rows = _read_csv(out / vocab.FILE_ORDERS)
    assert rows[0] == list(vocab.ORDER_COLUMNS)
    assert len(rows) - 1 == 120


def test_amazon_files_have_24_columns(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    for name in (vocab.FILE_AMAZON_US, vocab.FILE_AMAZON_DE, vocab.FILE_AMAZON_UNBALANCED):
        rows = _read_csv(out / name, delimiter="\t")
        assert rows[0] == list(vocab.AMAZON_V2_COLUMNS)
        assert len(rows[0]) == 24
        assert all(len(row) == 24 for row in rows)


def test_shopify_files_have_11_base_columns(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    required = set(vocab.SHOPIFY_COLUMNS)
    assert len(required) == 11
    for name in vocab.MATCH_RATE_SHOPIFY_FILES:
        rows = _read_csv(out / name)
        assert set(rows[0]) >= required
        assert rows[0] == list(vocab.SHOPIFY_COLUMNS)


def test_balanced_and_unbalanced_totals(tmp_path: Path) -> None:
    out, gen_samples, vocab = _generate(tmp_path)
    from crosserp.core.money import parse_amount

    for name, locale in ((vocab.FILE_AMAZON_US, "us"), (vocab.FILE_AMAZON_DE, "eu")):
        rows = _read_csv(out / name, delimiter="\t")
        header = rows[0]
        summary = dict(zip(header, rows[1], strict=True))
        assert summary["transaction-type"] == ""
        assert summary["total-amount"]
        total = parse_amount(summary["total-amount"], locale)
        summed = Decimal("0")
        for raw in rows[2:]:
            row = dict(zip(header, raw, strict=True))
            summed += parse_amount(row["amount"], locale)
        assert summed == total
    rows = _read_csv(out / vocab.FILE_AMAZON_UNBALANCED, delimiter="\t")
    header = rows[0]
    summary = dict(zip(header, rows[1], strict=True))
    total = parse_amount(summary["total-amount"], "us")
    summed = Decimal("0")
    for raw in rows[2:]:
        row = dict(zip(header, raw, strict=True))
        summed += parse_amount(row["amount"], "us")
    assert summed != total
    assert gen_samples.format_amount(summed, "us") != summary["total-amount"]


def test_anomalies_cover_every_scenario(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    anomalies = json.loads((out / vocab.FILE_ANOMALIES).read_text(encoding="utf-8"))
    assert isinstance(anomalies, list)
    scenarios = {item["scenario"] for item in anomalies}
    assert scenarios >= set(vocab.REQUIRED_SCENARIOS)
    chargeback_files = {item["file"] for item in anomalies if item["scenario"] == "chargeback"}
    assert any(name.startswith("amazon_") for name in chargeback_files)
    assert any(name.startswith("shopify_") for name in chargeback_files)
    for item in anomalies:
        assert set(item) >= {
            "scenario",
            "file",
            "row_nos",
            "order_id",
            "sku",
            "expected_issue_kind",
            "note",
        }
        path = out / item["file"]
        assert path.is_file()
        if path.suffix == ".tsv":
            rows = _read_csv(path, delimiter="\t")
        elif path.suffix == ".csv":
            rows = _read_csv(path)
        else:
            continue
        for row_no in item["row_nos"]:
            assert 1 <= row_no <= len(rows)
        if item["order_id"] and path.suffix in {".csv", ".tsv"}:
            blob = path.read_text(encoding="utf-8")
            assert item["order_id"] in blob


def test_expected_match_rate_at_least_95_percent(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    summary = json.loads((out / vocab.FILE_SUMMARY).read_text(encoding="utf-8"))
    anomalies = json.loads((out / vocab.FILE_ANOMALIES).read_text(encoding="utf-8"))
    rate = Decimal(summary["match_rate"])
    ratio = Decimal(summary["unmatched_ratio"])
    assert rate >= Decimal("0.95")
    assert ratio <= Decimal("0.05")
    unmatched_ids = {
        item["order_id"]
        for item in anomalies
        if item["expected_issue_kind"] in vocab.UNMATCHED_ISSUE_KINDS and item["order_id"]
    }
    groups: set[tuple[str, str, str]] = set()
    for name in vocab.MATCH_RATE_AMAZON_FILES:
        rows = _read_csv(out / name, delimiter="\t")
        header = rows[0]
        for raw in rows[1:]:
            row = dict(zip(header, raw, strict=True))
            if row["transaction-type"] not in vocab.ORDER_TRANSACTION_TYPES:
                continue
            if not row["order-id"]:
                continue
            groups.add(("amazon", row["order-id"], row["sku"]))
    for name in vocab.MATCH_RATE_SHOPIFY_FILES:
        rows = _read_csv(out / name)
        header = rows[0]
        for raw in rows[1:]:
            row = dict(zip(header, raw, strict=True))
            if row["Type"] not in vocab.SHOPIFY_ORDER_TYPES:
                continue
            if not row["Order"]:
                continue
            groups.add(("shopify", row["Order"], ""))
    unmatched = sum(1 for group in groups if group[1] in unmatched_ids)
    assert len(groups) == summary["order_type_group_count"]
    assert unmatched == summary["unmatched_order_type_group_count"]
    assert Decimal(len(groups) - unmatched) / Decimal(len(groups)) >= Decimal("0.95")


def test_text_files_are_utf8_lf_without_bom(tmp_path: Path) -> None:
    out, _gen, _vocab = _generate(tmp_path)
    seen = False
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix == ".xlsx":
            continue
        seen = True
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in raw
    assert seen


def test_buried_markers(tmp_path: Path) -> None:
    out, _gen, vocab = _generate(tmp_path)
    sku_map = (out / vocab.FILE_SKU_MAP).read_text(encoding="utf-8")
    assert "保温杯 🍵 黑色 500ml" in sku_map
    de_text = (out / vocab.FILE_AMAZON_DE).read_text(encoding="utf-8")
    assert "95,00" in de_text
    assert "1.234,56" not in de_text
    costs = _read_csv(out / vocab.FILE_COSTS)
    cup_rows = [row for row in costs[1:] if row[0] == "INT-CUP-500"]
    assert len(cup_rows) == 2
    fx_missing = (out / vocab.FILE_FX_MISSING_EUR).read_text(encoding="utf-8")
    assert "EUR" not in fx_missing
    assert "USD" in fx_missing
