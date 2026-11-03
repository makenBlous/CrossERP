"""原因码草稿与正式枚举的对照。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from crosserp.core.enums import IssueKind
from crosserp.issues.catalog import CATALOG, definition, render

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "src" / "crosserp" / "issues" / "catalog.yaml"
DOC_PATH = ROOT / "docs" / "rules" / "recon-categories.md"
ENUMS_PATH = ROOT / "src" / "crosserp" / "core" / "enums.py"

# 实施方案 6.1。T14 不创建 IssueKind。枚举文件落地后改为导入校验。
OFFICIAL_ISSUE_KINDS = frozenset(
    {
        "NOT_IN_ERP",
        "NOT_IN_SETTLEMENT",
        "QTY_MISMATCH",
        "AMOUNT_MISMATCH",
        "SKU_UNMAPPED",
        "COST_MISSING",
        "FX_MISSING",
        "CURRENCY_MISMATCH",
        "DUPLICATE_ROW",
        "REFUND_WITHOUT_ORDER",
        "UNKNOWN_FEE_TYPE",
        "SETTLEMENT_UNBALANCED",
        "PARSE_ERROR",
    }
)
CANDIDATE_ISSUE_KINDS = frozenset(
    {
        "FEE_OVERCHARGE",
        "SETTLEMENT_DELAYED",
        "CHARGEBACK",
        "PARTIAL_REFUND",
        "DUPLICATE_SETTLEMENT",
    }
)
CONFIRMED_MARK = "maken 已于 2026-11-02 确认"
SEVERITIES = frozenset({"info", "warn", "error"})
MATCH_RATE_EFFECTS = frozenset({"unmatched", "matched", "excluded", "order_side"})
SAMPLE_COVERAGE = frozenset({"covered", "conditional", "uncovered"})
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_BRACE = re.compile(r"\{[^{}]*\}")


def _load() -> dict[str, object]:
    loaded = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _codes() -> list[dict[str, object]]:
    raw = _load()["codes"]
    assert isinstance(raw, list)
    assert all(isinstance(item, dict) for item in raw)
    return raw


def _issue_kind_values() -> set[str]:
    if not ENUMS_PATH.is_file():
        return set(OFFICIAL_ISSUE_KINDS)
    from crosserp.core.enums import IssueKind

    return {member.value for member in IssueKind}


def _placeholders(template: str) -> list[str]:
    assert "{{" not in template
    assert "}}" not in template
    found = _PLACEHOLDER.findall(template)
    braces = _BRACE.findall(template)
    assert len(braces) == len(found)
    assert braces == [f"{{{name}}}" for name in found]
    return found


def test_official_codes_exist_in_issue_kind() -> None:
    """正式码必须都在 IssueKind 里。已确认的 5 个码在枚举落地后也必须写入。"""
    official = {item["code"] for item in _codes() if item["status"] == "official"}
    confirmed = {item["code"] for item in _codes() if item["status"] == "confirmed"}
    assert official == set(OFFICIAL_ISSUE_KINDS)
    assert confirmed == set(CANDIDATE_ISSUE_KINDS)
    kind_values = _issue_kind_values()
    assert official <= kind_values
    if ENUMS_PATH.is_file():
        assert confirmed <= kind_values


def test_confirmed_codes_stay_out_of_official_set() -> None:
    by_status: dict[str, set[str]] = {"official": set(), "confirmed": set()}
    for item in _codes():
        status = item["status"]
        assert status in by_status
        assert isinstance(item["code"], str)
        by_status[status].add(item["code"])
    assert by_status["confirmed"] == set(CANDIDATE_ISSUE_KINDS)
    assert by_status["official"].isdisjoint(by_status["confirmed"])
    for item in _codes():
        if item["status"] == "confirmed":
            assert item["confirmation"] == CONFIRMED_MARK
        else:
            assert "confirmation" not in item


def test_templates_use_legal_placeholders() -> None:
    for item in _codes():
        assert item["severity"] in SEVERITIES
        assert item["match_rate_effect"] in MATCH_RATE_EFFECTS
        assert item["sample_coverage"] in SAMPLE_COVERAGE
        assert isinstance(item["name_zh"], str) and item["name_zh"]
        assert isinstance(item["action"], str) and item["action"]
        templates = item["templates"]
        assert isinstance(templates, list) and templates
        for template in templates:
            assert isinstance(template, dict)
            text = template["text"]
            listed = template["placeholders"]
            assert isinstance(text, str) and text
            assert isinstance(listed, list)
            found = _placeholders(text)
            assert found
            assert set(found) == set(listed)
            assert all(isinstance(name, str) for name in listed)


def test_doc_lists_codes_sources_and_uncovered_samples() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for code in OFFICIAL_ISSUE_KINDS | CANDIDATE_ISSUE_KINDS:
        assert code in text
    assert text.count("github.com/") >= 2
    assert CONFIRMED_MARK in text
    assert "样本未覆盖" in text
    assert "未核实" in text


def test_runtime_catalog_matches_enum_and_renders_complete_detail() -> None:
    assert set(CATALOG) == {item.value for item in IssueKind}
    text = render(
        IssueKind.NOT_IN_ERP,
        {"order_id": "ORD-1", "sku": "SKU-1"},
    )
    assert "ORD-1" in text
    assert "SKU-1" in text
    assert "{缺:" not in text
    assert definition(IssueKind.NOT_IN_ERP).counts_as_unmatched is True
    assert definition(IssueKind.COST_MISSING).counts_as_unmatched is False


def test_runtime_catalog_marks_missing_template_fields() -> None:
    text = render(IssueKind.PARSE_ERROR, {"source_file": "input.csv", "row_no": 2})
    assert "input.csv" in text
    assert "{缺:error}" in text
