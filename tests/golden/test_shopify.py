"""Shopify 打款 golden。期望从 T08 样本和 summary.json 推导。不从导入器抄。"""

from __future__ import annotations

import csv
import json
import random
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.audit.log import verify_chain
from crosserp.connectors.base import FileConnector
from crosserp.connectors.importer import import_file
from crosserp.connectors.shopify_payouts import ShopifyPayoutsConnector
from crosserp.connectors.shopify_payouts.connector import _REQUIRED_COLUMNS
from crosserp.core.enums import ImportStatus, IssueKind
from crosserp.core.models import ColumnMapping, SettlementHeader, SettlementLineRec
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Fee, Issue, RawRow, Settlement, SettlementLine, Store
from crosserp.db.session import session_scope

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples" / "synthetic"
GOLDEN = Path(__file__).resolve().parent / "shopify"
USD = ColumnMapping(defaults={"currency": "USD"})
_BASE = list(_REQUIRED_COLUMNS)


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _load_json(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _expected(name: str) -> dict[str, object]:
    stem = name.removesuffix(".csv")
    return _load_json(GOLDEN / f"{stem}.expected.json")


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in headers})


def _sample_row(**overrides: str) -> dict[str, str]:
    row = {
        "Transaction Date": "2026-10-01 10:15:00 -0400",
        "Type": "charge",
        "Order": "SYN-ROW",
        "Card Brand": "Visa",
        "Card Source": "online",
        "Payout Status": "paid",
        "Payout Date": "2026-10-07",
        "Available On": "2026-10-07",
        "Amount": "10.00",
        "Fee": "0.20",
        "Net": "9.80",
    }
    row.update(overrides)
    return row


def _import_sample(engine: Engine, name: str) -> None:
    url = _url(engine)
    path = SAMPLES / name
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, ShopifyPayoutsConnector(), USD)
            assert result.status is ImportStatus.DONE
            assert result.error_count == 0
            expected = _expected(name)
            assert result.row_count == expected["data_rows"]
        with session_scope(engine) as session:
            _assert_snapshot(session, expected, name)
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def _assert_snapshot(session: Session, expected: dict[str, object], name: str) -> None:
    stores = session.scalars(select(Store)).all()
    assert len(stores) == 1
    store = stores[0]
    store_expected = expected["store"]
    assert isinstance(store_expected, dict)
    assert store.platform == store_expected["platform"]
    assert store.marketplace == store_expected["marketplace"]
    assert store.name == store_expected["name"]
    assert store.currency == expected["currency"]

    settlements = session.scalars(select(Settlement).order_by(Settlement.external_id)).all()
    expected_settlements = expected["settlements"]
    assert isinstance(expected_settlements, list)
    assert len(settlements) == len(expected_settlements)
    by_id = {item.external_id: item for item in settlements}
    file_total = Decimal("0")
    for item in expected_settlements:
        assert isinstance(item, dict)
        external_id = item["external_id"]
        assert isinstance(external_id, str)
        found = by_id[external_id]
        assert found.platform == "shopify"
        assert found.currency == item["currency"]
        assert found.total == Decimal(str(item["total"]))
        file_total += found.total
        assert _iso(found.deposit_date) == item["deposit_date"]
        assert found.period_start.isoformat() == item["period_start"]
        assert found.period_end.isoformat() == item["period_end"]
    assert file_total == Decimal(str(expected["file_total"]))

    raw_count = session.scalar(select(func.count()).select_from(RawRow))
    assert raw_count == expected["data_rows"]
    lines = session.scalars(select(SettlementLine)).all()
    expected_lines = expected["lines"]
    assert isinstance(expected_lines, list)
    assert len(lines) == len(expected_lines)
    rendered = sorted(
        (_line_view(session, line) for line in lines), key=lambda item: item["row_no"]
    )
    expected_rendered = sorted(
        (_expected_line(item) for item in expected_lines),
        key=lambda item: item["row_no"],
    )
    assert rendered == expected_rendered
    for line in lines:
        assert line.sku is None
        assert line.qty is None
        raw = session.get(RawRow, line.raw_row_id)
        assert raw is not None
        assert set(_BASE) <= set(raw.payload_json)

    issues = session.scalars(select(Issue)).all()
    expected_issues = expected["issues"]
    assert isinstance(expected_issues, list)
    assert len(issues) == len(expected_issues)
    actual_issues = sorted(
        (_issue_view(issue, name) for issue in issues),
        key=lambda item: (item["row_no"], item["kind"]),
    )
    expected_rendered_issues = sorted(
        (_expected_issue(item, name) for item in expected_issues),
        key=lambda item: (item["row_no"], item["kind"]),
    )
    assert actual_issues == expected_rendered_issues
    fee_count = session.scalar(select(func.count()).select_from(Fee))
    assert fee_count == 0


def _iso(value: object) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    assert callable(isoformat)
    rendered = isoformat()
    assert isinstance(rendered, str)
    return rendered


def _line_view(session: Session, line: SettlementLine) -> dict[str, object]:
    settlement = session.get(Settlement, line.settlement_id)
    assert settlement is not None
    raw = session.get(RawRow, line.raw_row_id)
    assert raw is not None
    assert line.posted_at is not None
    assert line.amount_description is not None
    return {
        "row_no": raw.row_no,
        "order_id": line.order_id,
        "amount_type": line.amount_type,
        "transaction_type": line.transaction_type,
        "amount": line.amount,
        "payout_status": line.amount_description.removeprefix("payout_status="),
        "posted_at": line.posted_at.isoformat(),
        "settlement_external_id": settlement.external_id,
    }


def _expected_line(item: object) -> dict[str, object]:
    assert isinstance(item, dict)
    return {
        "row_no": item["row_no"],
        "order_id": item["order_id"],
        "amount_type": item["amount_type"],
        "transaction_type": item["transaction_type"],
        "amount": Decimal(str(item["amount"])),
        "payout_status": item["payout_status"],
        "posted_at": item["posted_at"],
        "settlement_external_id": item["settlement_external_id"],
    }


def _issue_view(issue: Issue, name: str) -> dict[str, object]:
    detail = issue.detail_json
    assert isinstance(detail, dict)
    source = detail["source_file"]
    assert isinstance(source, str)
    assert source.endswith(name)
    return {
        "kind": issue.kind,
        "severity": issue.severity,
        "row_no": detail["row_no"],
        "order_id": detail["order_id"],
        "amount": detail["amount"],
        "fee": detail["fee"],
        "net": detail["net"],
        "expected_net": detail["expected_net"],
        "diff": detail["diff"],
    }


def _expected_issue(item: object, name: str) -> dict[str, object]:
    del name
    assert isinstance(item, dict)
    return {
        "kind": item["kind"],
        "severity": item["severity"],
        "row_no": item["row_no"],
        "order_id": item["order_id"],
        "amount": item["amount"],
        "fee": item["fee"],
        "net": item["net"],
        "expected_net": item["expected_net"],
        "diff": item["diff"],
    }


def _records(path: Path, mapping: ColumnMapping | None = None) -> list[object]:
    connector = ShopifyPayoutsConnector()
    rows = list(connector.read(path, mapping))
    found: list[object] = []
    for row in rows:
        found.extend(connector.normalize(row))
    return found


def test_shopify_expected_follows_t08_summary() -> None:
    summary = _load_json(SAMPLES / "expected" / "summary.json")
    files = summary["files"]
    assert isinstance(files, dict)
    loaded_anomalies: object = json.loads(
        (SAMPLES / "expected" / "anomalies.json").read_text(encoding="utf-8")
    )
    assert isinstance(loaded_anomalies, list)
    listed = loaded_anomalies
    for name in ("shopify_payout_2026-10-07.csv", "shopify_payout_2026-10-21.csv"):
        file_entry = files[name]
        assert isinstance(file_entry, dict)
        expected = _expected(name)
        settlements = expected["settlements"]
        assert isinstance(settlements, list)
        total = Decimal("0")
        for item in settlements:
            assert isinstance(item, dict)
            total += Decimal(str(item["total"]))
        assert total == Decimal(str(file_entry["total_amount"]))
        assert expected["data_rows"] == file_entry["data_rows"]
        assert expected["file_total"] == file_entry["total_amount"]
    net_rows = [
        item
        for item in listed
        if isinstance(item, dict) and item.get("scenario") == "shopify_net_mismatch"
    ]
    assert len(net_rows) == 1
    later = _expected("shopify_payout_2026-10-21.csv")
    issues = later["issues"]
    assert isinstance(issues, list)
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, dict)
    assert issue["kind"] == net_rows[0]["expected_issue_kind"]
    assert issue["row_no"] == net_rows[0]["row_nos"][0]
    assert issue["order_id"] == "SYN-SH-NET"
    assert issue["diff"] == "-0.60"


def test_shopify_connector_sniff_and_protocol() -> None:
    connector = ShopifyPayoutsConnector()
    assert isinstance(connector, FileConnector)
    assert connector.id == "shopify.payouts"
    assert connector.kind == "payout"
    assert connector.sniff(SAMPLES / "shopify_payout_2026-10-07.csv") == 0.9
    assert connector.sniff(SAMPLES / "shopify_payout_2026-10-21.csv") == 0.9
    amazon = SAMPLES / "amazon_us_2026-10-01_2026-10-14.tsv"
    assert connector.sniff(amazon) == 0.0


def test_shopify_entry_point_is_registered() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    needle = '"shopify.payouts" = "crosserp.connectors.shopify_payouts:ShopifyPayoutsConnector"'
    assert needle in text


def test_shopify_missing_columns_lists_them(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"
    headers = [name for name in _BASE if name not in {"Card Brand", "Net"}]
    _write_csv(path, headers, [_sample_row()])
    connector = ShopifyPayoutsConnector()
    with pytest.raises(ValueError, match="缺少基础列") as caught:
        list(connector.read(path, USD))
    message = str(caught.value)
    assert "Card Brand" in message
    assert "Net" in message


def test_shopify_without_currency_fails(tmp_path: Path) -> None:
    path = tmp_path / "noccy.csv"
    _write_csv(path, _BASE, [_sample_row()])
    with pytest.raises(ValueError, match="无法确定币种"):
        list(ShopifyPayoutsConnector().read(path))


def test_shopify_type_map_and_unknown_type(tmp_path: Path) -> None:
    path = tmp_path / "types.csv"
    rows = [
        _sample_row(Type="refund", Order="R1", Amount="-10.00", Fee="0.00", Net="-10.00"),
        _sample_row(Type="adjustment", Order="", Amount="1.00", Fee="0.00", Net="1.00"),
        _sample_row(Type="dispute", Order="D1", Amount="-5.00", Fee="0.00", Net="-5.00"),
        _sample_row(Type="SyntheticUnknown", Order="U1"),
    ]
    _write_csv(path, _BASE, rows)
    records = _records(path, USD)
    lines = [item for item in records if isinstance(item, SettlementLineRec)]
    assert [line.transaction_type for line in lines] == [
        "refund",
        "adjustment",
        "chargeback",
        "SyntheticUnknown",
    ]
    assert lines[2].amount_type == "dispute"
    assert lines[3].transaction_type == "SyntheticUnknown"
    kinds = [item.issue_kind for item in records if hasattr(item, "issue_kind")]
    assert kinds == [IssueKind.UNKNOWN_FEE_TYPE]


def test_shopify_eur_comma_decimal_uses_currency(tmp_path: Path) -> None:
    path = tmp_path / "eur.csv"
    row = _sample_row(Amount="20,00", Fee="0,40", Net="19,60", Currency="EUR")
    _write_csv(path, [*_BASE, "Currency"], [row])
    records = _records(path)
    headers = [item for item in records if isinstance(item, SettlementHeader)]
    lines = [item for item in records if isinstance(item, SettlementLineRec)]
    assert len(headers) == 1
    assert headers[0].currency == "EUR"
    assert headers[0].total == Decimal("19.60")
    assert lines[0].amount == Decimal("19.60")
    assert not any(hasattr(item, "issue_kind") for item in records)


def test_shopify_usd_comma_decimal_is_row_error(tmp_path: Path) -> None:
    path = tmp_path / "usd-comma.csv"
    row = _sample_row(Amount="20,00", Fee="0,40", Net="19,60", Currency="USD")
    _write_csv(path, [*_BASE, "Currency"], [row])
    records = _records(path)
    assert not any(isinstance(item, SettlementLineRec) for item in records)
    issues = [item for item in records if hasattr(item, "issue_kind")]
    assert len(issues) == 1
    assert issues[0].issue_kind is IssueKind.PARSE_ERROR


def test_shopify_payout_id_groups_separately(tmp_path: Path) -> None:
    path = tmp_path / "ids.csv"
    rows = [
        _sample_row(Order="A", Net="1.00", Amount="1.00", Fee="0.00", **{"Payout ID": "po_a"}),
        _sample_row(Order="B", Net="2.00", Amount="2.00", Fee="0.00", **{"Payout ID": "po_b"}),
        _sample_row(Order="C", Net="3.00", Amount="3.00", Fee="0.00", **{"Payout ID": "po_a"}),
    ]
    _write_csv(
        path, [*_BASE, "Payout ID", "Currency"], [{**row, "Currency": "USD"} for row in rows]
    )
    headers = [item for item in _records(path) if isinstance(item, SettlementHeader)]
    totals = {item.external_id: item.total for item in headers}
    assert totals == {"po_a": Decimal("4.00"), "po_b": Decimal("2.00")}


def test_shopify_unknown_column_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"
    row = _sample_row(**{"Seller Note": "不要猜"})
    _write_csv(path, [*_BASE, "Seller Note"], [row])
    connector = ShopifyPayoutsConnector()
    raw = next(iter(connector.read(path, USD)))
    assert raw.payload["Seller Note"] == "不要猜"
    line = next(item for item in connector.normalize(raw) if isinstance(item, SettlementLineRec))
    assert line.sku is None


@pytest.mark.db
def test_shopify_golden_2026_10_07(engine: Engine) -> None:
    _import_sample(engine, "shopify_payout_2026-10-07.csv")


@pytest.mark.db
def test_shopify_golden_2026_10_21_keeps_wrong_net(engine: Engine) -> None:
    _import_sample(engine, "shopify_payout_2026-10-21.csv")


@pytest.mark.db
def test_shopify_shuffled_columns_match_golden(engine: Engine, tmp_path: Path) -> None:
    source = SAMPLES / "shopify_payout_2026-10-07.csv"
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header, *body = rows
    order = list(range(len(header)))
    random.Random(11).shuffle(order)
    assert order != list(range(len(header)))
    shuffled = tmp_path / "shuffled.csv"
    with shuffled.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([header[index] for index in order])
        for row in body:
            writer.writerow([row[index] for index in order])
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, shuffled, ShopifyPayoutsConnector(), USD)
            assert result.status is ImportStatus.DONE
        with session_scope(engine) as session:
            _assert_snapshot(session, _expected("shopify_payout_2026-10-07.csv"), shuffled.name)
    finally:
        downgrade_base(url)


@pytest.mark.db
def test_shopify_optional_columns_can_be_removed(engine: Engine, tmp_path: Path) -> None:
    optional = [
        "Checkout",
        "Payment Method Name",
        "Presentment Amount",
        "Presentment Currency",
        "Currency",
        "Payout ID",
    ]
    full_row = _sample_row(
        Checkout="chk_1",
        **{
            "Payment Method Name": "card",
            "Presentment Amount": "10.00",
            "Presentment Currency": "USD",
            "Currency": "USD",
            "Payout ID": "po_keep",
        },
    )
    full = tmp_path / "with-optional.csv"
    stripped = tmp_path / "without-optional.csv"
    _write_csv(full, [*_BASE, *optional], [full_row])
    _write_csv(stripped, _BASE, [_sample_row()])
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            with_optional = import_file(session, full, ShopifyPayoutsConnector())
            without = import_file(session, stripped, ShopifyPayoutsConnector(), USD)
            assert with_optional.status is ImportStatus.DONE
            assert without.status is ImportStatus.DONE
        with session_scope(engine) as session:
            raws = session.scalars(select(RawRow)).all()
            kept = next(row for row in raws if row.payload_json.get("Payout ID") == "po_keep")
            assert kept.payload_json["Checkout"] == "chk_1"
            assert "Checkout" not in next(row.payload_json for row in raws if row.id != kept.id)
            settlements = session.scalars(select(Settlement)).all()
            assert {item.external_id for item in settlements} == {
                "po_keep",
                "payout-date:2026-10-07",
            }
            amounts = session.scalars(select(SettlementLine.amount)).all()
            assert len(amounts) == 2
            assert all(amount == Decimal("9.80") for amount in amounts)
    finally:
        downgrade_base(url)


@pytest.mark.db
def test_shopify_batch_fails_when_currency_missing(engine: Engine) -> None:
    url = _url(engine)
    path = SAMPLES / "shopify_payout_2026-10-07.csv"
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, ShopifyPayoutsConnector())
            assert result.status is ImportStatus.FAILED
            assert result.row_count == 0
            assert result.message is not None
            assert "无法确定币种" in result.message
        with session_scope(engine) as session:
            assert session.scalar(select(func.count()).select_from(RawRow)) == 0
            assert session.scalar(select(func.count()).select_from(Settlement)) == 0
    finally:
        downgrade_base(url)
