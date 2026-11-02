"""Amazon V2 golden。期望来自 T08 标准答案。不从实现输出回抄。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine

from crosserp.connectors.amazon_settlement_v2 import AmazonSettlementV2Connector
from crosserp.connectors.amazon_settlement_v2.connector import load_fee_map
from crosserp.connectors.amazon_settlement_v2.dates import parse_amazon_date
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus, IssueKind
from crosserp.core.errors import AmountParseError
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Fee, Issue, RawRow, Settlement, SettlementLine, Store
from crosserp.db.session import session_scope

REPO = Path(__file__).resolve().parents[2]
SAMPLES = REPO / "samples" / "synthetic"
EXPECTED_DIR = Path(__file__).parent / "amazon_v2"

# 与 scripts/sample_vocab.py 的 KNOWN_FEE_PAIRS 一致。不是平台全集。
_SYNTHETIC_PAIRS = frozenset(
    {
        ("ItemPrice", "Principal"),
        ("ItemFees", "Commission"),
        ("ItemFees", "FBAPerUnitFulfillmentFee"),
    }
)


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _expected(name: str) -> dict[str, object]:
    path = EXPECTED_DIR / f"{name}.expected.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _decimal(value: object) -> Decimal:
    assert isinstance(value, str)
    return Decimal(value)


def _moment(value: object) -> datetime:
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _import_sample(engine: Engine, name: str) -> None:
    url = _url(engine)
    upgrade_head(url)
    with session_scope(engine) as session:
        result = import_file(session, SAMPLES / name, AmazonSettlementV2Connector())
        assert result.status is ImportStatus.DONE
        assert result.error_count == 0


def _assert_amazon_golden(engine: Engine, name: str) -> None:
    expected = _expected(name)
    try:
        _import_sample(engine, name)
        with session_scope(engine) as session:
            _assert_header(session, expected)
            _assert_store(session, expected)
            _assert_counts(session, expected)
            _assert_fees(session, expected)
            _assert_issues(session, expected)
            _assert_summary_not_a_line(session, expected)
            _assert_stored_rows(session, expected)
    finally:
        downgrade_base(_url(engine))


def _assert_header(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    header = expected["settlement"]
    assert isinstance(header, dict)
    rows = session.scalars(select(Settlement)).all()
    assert len(rows) == 1
    settlement = rows[0]
    assert settlement.external_id == header["external_id"]
    assert settlement.currency == header["currency"]
    assert settlement.platform == "amazon"
    assert settlement.total == _decimal(header["total"])
    assert settlement.period_start == _moment(header["period_start"])
    assert settlement.period_end == _moment(header["period_end"])
    assert settlement.deposit_date == _moment(header["deposit_date"])


def _assert_store(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    wanted = expected["store"]
    assert isinstance(wanted, dict)
    stores = session.scalars(select(Store)).all()
    assert len(stores) == 1
    store = stores[0]
    assert store.platform == wanted["platform"]
    assert store.marketplace == wanted["marketplace"]
    assert store.currency == wanted["currency"]
    assert store.name == wanted["marketplace"]


def _assert_counts(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    raw_rows = session.scalars(select(RawRow)).all()
    lines = session.scalars(select(SettlementLine)).all()
    assert len(raw_rows) == expected["raw_row_count"]
    assert len(lines) == expected["settlement_line_count"]
    skipped = expected["not_inserted_row_nos"]
    assert isinstance(skipped, list)
    raw_by_no = {row.row_no: row.id for row in raw_rows}
    linked = {line.raw_row_id for line in lines}
    for row_no in skipped:
        assert isinstance(row_no, int)
        assert raw_by_no[row_no] not in linked


def _assert_fees(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    wanted = expected["fee_totals"]
    assert isinstance(wanted, dict)
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    fees = session.scalars(select(Fee)).all()
    lines = session.scalars(select(SettlementLine)).all()
    assert len(fees) == len(lines)
    for fee in fees:
        totals[fee.fee_category] += fee.amount
    assert set(totals) == set(wanted)
    for category, text in wanted.items():
        assert isinstance(category, str)
        assert totals[category] == _decimal(text)


def _assert_issues(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    wanted = expected["issues"]
    assert isinstance(wanted, list)
    found = session.scalars(select(Issue)).all()
    assert len(found) == len(wanted)
    actual = sorted(
        (issue.kind, issue.severity, issue.detail_json.get("row_no")) for issue in found
    )
    expected_keys = []
    details = {(issue.kind, issue.detail_json.get("row_no")): issue for issue in found}
    for item in wanted:
        assert isinstance(item, dict)
        expected_keys.append((item["kind"], item["severity"], item["row_no"]))
        issue = details[(item["kind"], item["row_no"])]
        for key in ("total_amount", "line_sum", "diff"):
            if key in item:
                assert issue.detail_json[key] == item[key]
    assert actual == sorted(expected_keys)


def _assert_summary_not_a_line(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    row_no = expected["summary_row_no"]
    assert isinstance(row_no, int)
    raw = session.scalar(select(RawRow).where(RawRow.row_no == row_no))
    assert raw is not None
    assert raw.payload_json["transaction-type"].strip() == ""
    assert raw.payload_json["total-amount"].strip() != ""
    linked = session.scalar(select(SettlementLine).where(SettlementLine.raw_row_id == raw.id))
    assert linked is None


def _assert_stored_rows(session: object, expected: dict[str, object]) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    wanted = expected["stored_rows"]
    assert isinstance(wanted, list)
    for item in wanted:
        assert isinstance(item, dict)
        row_no = item["row_no"]
        assert isinstance(row_no, int)
        raw = session.scalar(select(RawRow).where(RawRow.row_no == row_no))
        assert raw is not None
        line = session.scalar(select(SettlementLine).where(SettlementLine.raw_row_id == raw.id))
        assert line is not None
        assert line.amount == _decimal(item["amount"])
        assert line.amount_description == item["amount_description"]
        if "order_id" in item:
            assert line.order_id == item["order_id"]
        if "fee_category" in item:
            fee = session.scalar(select(Fee).where(Fee.settlement_line_id == line.id))
            assert fee is not None
            assert fee.fee_category == item["fee_category"]
            assert fee.amount == line.amount


def _shuffle(source: Path, target: Path) -> None:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames is not None
        rows = list(reader)
        names = list(reversed(reader.fieldnames))
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=names,
            delimiter="\t",
            lineterminator="\n",
            quoting=csv.QUOTE_NONE,
        )
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.db
def test_amazon_us_golden(engine: Engine) -> None:
    _assert_amazon_golden(engine, "amazon_us_2026-10-01_2026-10-14.tsv")


@pytest.mark.db
def test_amazon_de_golden_parses_comma_amount(engine: Engine) -> None:
    _assert_amazon_golden(engine, "amazon_de_2026-10-01_2026-10-14.tsv")


@pytest.mark.db
def test_amazon_unbalanced_has_one_issue(engine: Engine) -> None:
    _assert_amazon_golden(engine, "amazon_us_unbalanced.tsv")
    expected = _expected("amazon_us_unbalanced.tsv")
    issues = expected["issues"]
    assert isinstance(issues, list)
    assert len(issues) == 1
    assert issues[0]["kind"] == IssueKind.SETTLEMENT_UNBALANCED.value


@pytest.mark.db
def test_amazon_shuffled_columns_match_us_golden(engine: Engine, tmp_path: Path) -> None:
    name = "amazon_us_2026-10-01_2026-10-14.tsv"
    shuffled = tmp_path / name
    _shuffle(SAMPLES / name, shuffled)
    expected = _expected(name)
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, shuffled, AmazonSettlementV2Connector())
            assert result.status is ImportStatus.DONE
            assert result.error_count == 0
            _assert_header(session, expected)
            _assert_counts(session, expected)
            _assert_fees(session, expected)
            _assert_issues(session, expected)
            _assert_stored_rows(session, expected)
    finally:
        downgrade_base(url)


@pytest.mark.db
def test_amazon_unknown_column_is_kept(engine: Engine, tmp_path: Path) -> None:
    path = tmp_path / "extra.tsv"
    path.write_text(
        "settlement-id\ttotal-amount\tcurrency\ttransaction-type\t"
        "amount-type\tamount-description\tamount\tmarketplace-name\t"
        "settlement-start-date\tsettlement-end-date\tseller-note\n"
        "S-1\t10.00\tUSD\t\t\t\t\tAmazon.com\t2026-10-01\t2026-10-14\thello\n"
        "S-1\t\tUSD\tOrder\tItemPrice\tPrincipal\t10.00\tAmazon.com\t"
        "2026-10-01\t2026-10-14\tkeep-me\n",
        encoding="utf-8",
    )
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, AmazonSettlementV2Connector())
            assert result.status is ImportStatus.DONE
            assert result.error_count == 1
            issues = session.scalars(select(Issue)).all()
            infos = [issue for issue in issues if issue.severity == "info"]
            assert len(infos) == 1
            assert infos[0].kind == IssueKind.PARSE_ERROR.value
            assert infos[0].detail_json["error"] == "未知列已保留"
            assert infos[0].detail_json["columns"] == ["seller-note"]
            raw_rows = session.scalars(select(RawRow)).all()
            assert all("seller-note" in row.payload_json for row in raw_rows)
            assert session.scalar(select(SettlementLine)) is not None
            unbalanced = [
                issue for issue in issues if issue.kind == IssueKind.SETTLEMENT_UNBALANCED.value
            ]
            assert unbalanced == []
    finally:
        downgrade_base(url)


@pytest.mark.db
def test_amazon_missing_column_fails_batch(engine: Engine, tmp_path: Path) -> None:
    path = tmp_path / "missing.tsv"
    path.write_text("settlement-id\tcurrency\nA\tUSD\n", encoding="utf-8")
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, AmazonSettlementV2Connector())
            assert result.status is ImportStatus.FAILED
            assert result.message is not None
            assert "缺少必需列" in result.message
            assert "amount" in result.message
            assert session.scalar(select(Settlement)) is None
            assert session.scalar(select(RawRow)) is None
    finally:
        downgrade_base(url)


@pytest.mark.db
def test_amazon_bad_amount_does_not_stop_batch(engine: Engine, tmp_path: Path) -> None:
    path = tmp_path / "bad.tsv"
    header = (
        "settlement-id\ttotal-amount\tcurrency\ttransaction-type\tamount-type\t"
        "amount-description\tamount\tmarketplace-name\tsettlement-start-date\t"
        "settlement-end-date\n"
    )
    body = (
        "S-2\t10.00\tUSD\t\t\t\t\tAmazon.com\t2026-10-01\t2026-10-14\n"
        "S-2\t\tUSD\tOrder\tItemPrice\tPrincipal\t10.00\tAmazon.com\t2026-10-01\t2026-10-14\n"
        "S-2\t\tUSD\tOrder\tItemPrice\tPrincipal\tabc\tAmazon.com\t2026-10-01\t2026-10-14\n"
    )
    path.write_text(header + body, encoding="utf-8")
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, AmazonSettlementV2Connector())
            assert result.status is ImportStatus.DONE
            lines = session.scalars(select(SettlementLine)).all()
            assert len(lines) == 1
            assert lines[0].amount == Decimal("10.00")
            issues = session.scalars(select(Issue)).all()
            parse_errors = [issue for issue in issues if issue.kind == IssueKind.PARSE_ERROR.value]
            assert len(parse_errors) == 1
            assert "abc" in parse_errors[0].detail_json["error"]
            assert all(issue.kind != IssueKind.SETTLEMENT_UNBALANCED.value for issue in issues)
    finally:
        downgrade_base(url)


def test_amazon_fee_map_is_only_synthetic_pairs() -> None:
    assert set(load_fee_map()) == _SYNTHETIC_PAIRS


def test_amazon_sniff_de_sample() -> None:
    score = AmazonSettlementV2Connector().sniff(SAMPLES / "amazon_de_2026-10-01_2026-10-14.tsv")
    assert score == 0.95


def test_amazon_sniff_rejects_other_files() -> None:
    connector = AmazonSettlementV2Connector()
    assert connector.sniff(SAMPLES / "shopify_payout_2026-10-07.csv") == 0.0
    assert connector.sniff(SAMPLES / "orders.csv") == 0.0


def test_amazon_sniff_accepts_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.tsv"
    path.write_text(
        "settlement-id\tamount-type\tamount-description\ttotal-amount\n",
        encoding="utf-8-sig",
    )
    assert AmazonSettlementV2Connector().sniff(path) == 0.95


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-10-14", datetime(2026, 10, 14, tzinfo=UTC)),
        ("2026-10-14 07:00:00 UTC", datetime(2026, 10, 14, 7, 0, 0, tzinfo=UTC)),
        ("2026-10-01 12:00:00 UTC", datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)),
        ("14.10.2026", datetime(2026, 10, 14, tzinfo=UTC)),
        ("2026-10-14T07:00:00Z", datetime(2026, 10, 14, 7, 0, 0, tzinfo=UTC)),
        ("2026-10-14T09:00:00+02:00", datetime(2026, 10, 14, 7, 0, 0, tzinfo=UTC)),
        ("2026-10-14T07:00:00.000Z", datetime(2026, 10, 14, 7, 0, 0, tzinfo=UTC)),
    ],
)
def test_parse_amazon_date_formats(text: str, expected: datetime) -> None:
    # 这些格式都待真实数据验证。
    assert parse_amazon_date(text) == expected


def test_parse_amazon_date_empty_is_none() -> None:
    assert parse_amazon_date("  ") is None


def test_parse_amazon_date_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="无法解析日期"):
        parse_amazon_date("2026-10-14 07:00:00 utc")
    with pytest.raises(ValueError, match="无法解析日期"):
        parse_amazon_date("32.13.2026")


def test_parse_amazon_date_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        parse_amazon_date(None)  # type: ignore[arg-type]


def test_parse_amount_eu_sample_text() -> None:
    from crosserp.core.money import parse_amount

    assert parse_amount("95,00", "eu") == Decimal("95.00")
    with pytest.raises(AmountParseError):
        parse_amount("95,00", "us")
