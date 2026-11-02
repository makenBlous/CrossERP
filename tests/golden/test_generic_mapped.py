"""通用映射导入。合成样本行数、表头错误、占位 YAML、生效期和 xlsx/csv 对照。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook
from python_calamine import CalamineWorkbook
from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from crosserp.audit.log import verify_chain
from crosserp.connectors.base import FileConnector
from crosserp.connectors.generic_mapped.connector import GenericMappedConnector
from crosserp.connectors.generic_mapped.mapping import MappingError, load_mapping
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus, IssueKind
from crosserp.core.models import ColumnMapping
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AuditLog, FxRate, Issue, OrderLine, RawRow, Sku, SkuCost, Store
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[2]
SYNTH = ROOT / "samples" / "synthetic"
MAPPINGS = ROOT / "src" / "crosserp" / "connectors" / "mappings"
TEMPLATES = ROOT / "samples" / "templates"
_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
_CUP_NEXT = datetime(2026, 10, 10, tzinfo=UTC)


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _summary() -> dict[str, object]:
    loaded = json.loads((SYNTH / "expected" / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError("summary.json 不是对象")
    return loaded


def _data_rows(name: str) -> int:
    files = _summary()["files"]
    if not isinstance(files, dict):
        raise AssertionError("summary.json 没有 files")
    entry = files[name]
    if not isinstance(entry, dict) or not isinstance(entry["data_rows"], int):
        raise AssertionError(f"{name} 没有 data_rows")
    return entry["data_rows"]


def _count(session: object, model: type[object]) -> int:
    from sqlalchemy.orm import Session

    if not isinstance(session, Session):
        raise AssertionError("session 类型不对")
    value = session.scalar(select(func.count()).select_from(model))
    assert isinstance(value, int)
    return value


def test_mapped_sniff_is_always_zero(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text("order_id\nA\n", encoding="utf-8")
    connector = GenericMappedConnector()
    assert connector.sniff(path) == 0.0
    assert isinstance(connector, FileConnector)
    assert connector.id == "generic.mapped"


def test_mapped_entry_point_is_registered() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'mapped = "crosserp.connectors.generic_mapped.connector:GenericMappedConnector"' in text


def test_mapped_todo_yaml_is_rejected() -> None:
    for name in ("lingxing_orders.yaml", "sellfox_orders.yaml"):
        path = MAPPINGS / name
        text = path.read_text(encoding="utf-8")
        assert "待真实数据验证" in text
        with pytest.raises(MappingError, match="请先填写真实表头"):
            load_mapping(path)


def test_mapped_templates_have_header_and_example() -> None:
    costs = _xlsx_rows(TEMPLATES / "costs.xlsx")
    rates = _xlsx_rows(TEMPLATES / "fx_rates.xlsx")
    assert costs[0] == ["内部SKU", "采购单价", "头程单价", "币种", "生效日期"]
    assert costs[1][0] == "EXAMPLE-SKU"
    assert len(costs) == 2
    assert rates[0] == ["月份", "原币", "目标币", "汇率"]
    assert rates[1][0] == "2026-01"
    assert len(rates) == 2


def test_mapped_orders_costs_fx_and_sku(engine: Engine) -> None:
    url = _url(engine)
    orders = load_mapping(SYNTH / "mappings" / "synthetic_orders.yaml")
    costs = load_mapping(MAPPINGS / "template_costs.yaml")
    rates = load_mapping(MAPPINGS / "template_fx_rates.yaml")
    skus = load_mapping(MAPPINGS / "template_sku.yaml")
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            order_result = import_file(
                session, SYNTH / "orders.csv", GenericMappedConnector(), orders
            )
            cost_csv = import_file(session, SYNTH / "costs.csv", GenericMappedConnector(), costs)
            fx_xlsx = import_file(session, SYNTH / "fx_rates.xlsx", GenericMappedConnector(), rates)
            sku_result = import_file(session, SYNTH / "sku_map.csv", GenericMappedConnector(), skus)
            assert order_result.status is ImportStatus.DONE
            assert order_result.row_count == _data_rows("orders.csv")
            assert order_result.error_count == 0
            assert cost_csv.row_count == _data_rows("costs.csv")
            assert cost_csv.error_count == 0
            assert fx_xlsx.row_count == _data_rows("fx_rates.xlsx")
            assert fx_xlsx.error_count == 0
            assert sku_result.row_count == _data_rows("sku_map.csv")
            assert sku_result.error_count == 0
        with session_scope(engine) as session:
            assert _count(session, OrderLine) == _data_rows("orders.csv")
            assert _count(session, SkuCost) == _data_rows("costs.csv")
            assert _count(session, FxRate) == _data_rows("fx_rates.csv")
            assert _count(session, Sku) == _data_rows("sku_map.csv")
            line = session.scalar(
                select(OrderLine).where(OrderLine.platform_order_id == "SYN-US-0001")
            )
            assert line is not None
            assert line.qty == 1
            assert line.item_price == Decimal("25.04")
            assert line.currency == "USD"
            assert line.order_date == datetime(2026, 10, 1, tzinfo=UTC)
            assert line.platform_sku == "CUP-US-001"
            store = session.get(Store, line.store_id)
            assert store is not None
            assert store.platform == "amazon"
            assert store.name == "amazon-us"
            assert store.marketplace == "Amazon.com"
            assert store.currency == "USD"
            raw = session.get(RawRow, line.raw_row_id)
            assert raw is not None
            assert raw.payload_json["order_id"] == "SYN-US-0001"
            assert "currency" in raw.payload_json
            audit = session.scalar(
                select(AuditLog).where(AuditLog.target_id == str(order_result.batch_id))
            )
            assert audit is not None
            assert audit.after_json is not None
            assert audit.after_json["source_name"] == "synthetic_orders"
            _assert_costs_match(session)
            _assert_rates_match(session)
            title = session.scalar(select(Sku).where(Sku.internal_sku == "INT-CUP-500"))
            assert title is not None
            assert title.title == "保温杯 🍵 黑色 500ml"
            assert title.active is True
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_mapped_xlsx_matches_csv(engine: Engine) -> None:
    url = _url(engine)
    costs = load_mapping(MAPPINGS / "template_costs.yaml")
    rates = load_mapping(MAPPINGS / "template_fx_rates.yaml")
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            import_file(session, SYNTH / "costs.csv", GenericMappedConnector(), costs)
            import_file(session, SYNTH / "fx_rates.csv", GenericMappedConnector(), rates)
            cost_csv = _cost_signatures(session)
            fx_csv = _fx_signatures(session)
        downgrade_base(url)
        upgrade_head(url)
        with session_scope(engine) as session:
            import_file(session, SYNTH / "costs.xlsx", GenericMappedConnector(), costs)
            import_file(session, SYNTH / "fx_rates.xlsx", GenericMappedConnector(), rates)
            assert _cost_signatures(session) == cost_csv
            assert _fx_signatures(session) == fx_csv
            assert len(cost_csv) == _data_rows("costs.csv")
            assert len(fx_csv) == _data_rows("fx_rates.csv")
    finally:
        downgrade_base(url)


def test_mapped_missing_header_lists_actual_headers(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    mapping_path = tmp_path / "bad.yaml"
    mapping_path.write_text(
        """
target: order_line
source_name: bad_headers
timezone: UTC
amount_locale: us
date_formats: ["%Y-%m-%d"]
columns:
  platform_order_id: "不存在的列"
  order_item_id: order_item_id
  store: store
  platform_sku: platform_sku
  qty: qty
  order_date: order_date
  item_price: item_price
  currency: currency
""".strip()
        + "\n",
        encoding="utf-8",
    )
    mapping = load_mapping(mapping_path)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, SYNTH / "orders.csv", GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.FAILED
            assert result.row_count == 0
            assert result.message is not None
            assert (
                "YAML 里的 platform_order_id 对应的表头 不存在的列 在文件里不存在" in result.message
            )
            assert "文件实际表头是" in result.message
            assert "order_id" in result.message
            assert "platform_sku" in result.message
    finally:
        downgrade_base(url)


def test_mapped_todo_column_mapping_is_rejected(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "one.csv"
    path.write_text("订单号\nA\n", encoding="utf-8")
    mapping = ColumnMapping(
        target="order_line",
        source_name="todo",
        timezone="UTC",
        amount_locale="us",
        date_formats=["%Y-%m-%d"],
        columns={"platform_order_id": "TODO_订单号"},
        defaults={"store": "amazon-us"},
    )
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.FAILED
            assert result.message is not None
            assert "请先填写真实表头" in result.message
    finally:
        downgrade_base(url)


def test_mapped_cost_overlap_names_both_spans(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "overlap.csv"
    path.write_text(
        "内部SKU,采购单价,头程单价,币种,生效日期,结束日期\n"
        "INT-OVER,1.00,0.10,CNY,2026-01-01,2026-06-01\n"
        "INT-OVER,2.00,0.20,CNY,2026-03-01,2026-08-01\n"
        "INT-OK,3.00,0.30,CNY,2026-01-01,\n",
        encoding="utf-8",
    )
    mapping = _cost_mapping(tmp_path, with_end=True)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.DONE
            assert result.row_count == 3
            assert result.error_count == 2
        with session_scope(engine) as session:
            assert _count(session, SkuCost) == 1
            kept = session.scalars(select(SkuCost)).one()
            assert kept.internal_sku == "INT-OK"
            issues = session.scalars(select(Issue)).all()
            assert len(issues) == 2
            assert {issue.kind for issue in issues} == {IssueKind.PARSE_ERROR.value}
            detail = str(issues[0].detail_json)
            assert "INT-OVER" in detail
            assert "2026-01-01" in detail
            assert "2026-03-01" in detail
            assert "冲突" in detail
    finally:
        downgrade_base(url)


def test_mapped_cost_overlap_with_existing_row(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text(
        "内部SKU,采购单价,头程单价,币种,生效日期\nINT-OLD,1.00,0.10,CNY,2026-01-01\n",
        encoding="utf-8",
    )
    second.write_text(
        "内部SKU,采购单价,头程单价,币种,生效日期\nINT-OLD,2.00,0.20,CNY,2026-06-01\n",
        encoding="utf-8",
    )
    mapping = load_mapping(MAPPINGS / "template_costs.yaml")
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            assert import_file(session, first, GenericMappedConnector(), mapping).error_count == 0
        with session_scope(engine) as session:
            result = import_file(session, second, GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.DONE
            assert result.error_count == 1
        with session_scope(engine) as session:
            assert _count(session, SkuCost) == 1
            issue = session.scalars(select(Issue)).one()
            detail = str(issue.detail_json)
            assert "已有记录" in detail
            assert "INT-OLD" in detail
            assert "2026-01-01" in detail
            assert "2026-06-01" in detail
    finally:
        downgrade_base(url)


def test_mapped_fx_upsert_writes_audit(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    revised = tmp_path / "fx.csv"
    revised.write_text("月份,原币,目标币,汇率\n2026-10,USD,CNY,7.30000000\n", encoding="utf-8")
    mapping = load_mapping(MAPPINGS / "template_fx_rates.yaml")
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            import_file(session, SYNTH / "fx_rates.csv", GenericMappedConnector(), mapping)
        with session_scope(engine) as session:
            result = import_file(session, revised, GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.DONE
            assert result.error_count == 0
        with session_scope(engine) as session:
            assert _count(session, FxRate) == 2
            usd = session.scalar(
                select(FxRate).where(FxRate.from_ccy == "USD", FxRate.to_ccy == "CNY")
            )
            eur = session.scalar(
                select(FxRate).where(FxRate.from_ccy == "EUR", FxRate.to_ccy == "CNY")
            )
            assert usd is not None
            assert eur is not None
            assert usd.rate == Decimal("7.30000000")
            assert eur.rate == Decimal("7.85000000")
            assert usd.source == "template_fx_rates"
            audit = session.scalar(select(AuditLog).where(AuditLog.action == "fx_rate_upsert"))
            assert audit is not None
            assert audit.reason == "同月同币对覆盖"
            assert audit.before_json is not None
            assert audit.after_json is not None
            assert audit.before_json["rate"] == "7.25000000"
            assert audit.after_json["rate"] == "7.30000000"
            assert audit.target_id == str(usd.id)
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_mapped_unknown_column_is_kept(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    path.write_text(
        "order_id,order_item_id,store,platform_sku,qty,order_date,item_price,currency,备注\n"
        "SYN-1,SYN-1-1,amazon-us,CUP-US-001,1,2026-10-01,10.00,USD,不要当成金额\n",
        encoding="utf-8",
    )
    mapping = load_mapping(SYNTH / "mappings" / "synthetic_orders.yaml")
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, GenericMappedConnector(), mapping)
            assert result.status is ImportStatus.DONE
            assert result.error_count == 0
        with session_scope(engine) as session:
            raw = session.scalars(select(RawRow)).one()
            assert raw.payload_json["备注"] == "不要当成金额"
            line = session.scalars(select(OrderLine)).one()
            assert line.item_price == Decimal("10.00")
    finally:
        downgrade_base(url)


def test_mapped_header_row_and_skip_rows(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "costs.csv"
    path.write_text(
        "这是标题\n"
        "内部SKU,采购单价,头程单价,币种,生效日期\n"
        "这行跳过\n"
        "INT-SKIP,4.00,0.40,CNY,2026-02-01\n",
        encoding="utf-8",
    )
    mapping_path = tmp_path / "map.yaml"
    mapping_path.write_text(
        """
target: sku_cost
source_name: skip_demo
sheet: 0
header_row: 2
skip_rows: 1
encoding: utf-8-sig
amount_locale: us
date_formats: ["%Y-%m-%d"]
timezone: UTC
columns:
  internal_sku: "内部SKU"
  unit_cost: "采购单价"
  freight_per_unit: "头程单价"
  currency: "币种"
  valid_from: "生效日期"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(
                session, path, GenericMappedConnector(), load_mapping(mapping_path)
            )
            assert result.row_count == 1
            assert result.error_count == 0
        with session_scope(engine) as session:
            row = session.scalars(select(SkuCost)).one()
            assert row.internal_sku == "INT-SKIP"
            assert row.valid_from == datetime(2026, 2, 1, tzinfo=UTC)
            raw = session.scalars(select(RawRow)).one()
            assert raw.row_no == 4
    finally:
        downgrade_base(url)


def test_mapped_gb18030_csv(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "costs.csv"
    path.write_bytes(
        "内部SKU,采购单价,头程单价,币种,生效日期\nINT-GB,5.00,0.50,CNY,2026-03-01\n".encode(
            "gb18030"
        )
    )
    mapping_path = tmp_path / "map.yaml"
    text = (MAPPINGS / "template_costs.yaml").read_text(encoding="utf-8")
    mapping_path.write_text(
        text.replace("encoding: utf-8-sig", "encoding: gb18030"), encoding="utf-8"
    )
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(
                session, path, GenericMappedConnector(), load_mapping(mapping_path)
            )
            assert result.status is ImportStatus.DONE
            assert result.row_count == 1
            assert result.error_count == 0
        with session_scope(engine) as session:
            row = session.scalars(select(SkuCost)).one()
            assert row.internal_sku == "INT-GB"
            assert row.unit_cost == Decimal("5.00")
    finally:
        downgrade_base(url)


def test_mapped_numeric_xlsx_cell_is_rejected(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "costs.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["内部SKU", "采购单价", "头程单价", "币种", "生效日期"])
    sheet.append(["INT-NUM", 12.5, "1.00", "CNY", "2026-01-01"])
    workbook.save(path)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(
                session,
                path,
                GenericMappedConnector(),
                load_mapping(MAPPINGS / "template_costs.yaml"),
            )
            assert result.status is ImportStatus.FAILED
            assert result.message is not None
            assert "float" in result.message
    finally:
        downgrade_base(url)


def _cost_signatures(session: object) -> set[tuple[object, ...]]:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    rows = session.scalars(select(SkuCost)).all()
    return {
        (
            row.internal_sku,
            row.valid_from,
            row.valid_to,
            row.unit_cost,
            row.freight_per_unit,
            row.currency,
        )
        for row in rows
    }


def _fx_signatures(session: object) -> set[tuple[object, ...]]:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    rows = session.scalars(select(FxRate)).all()
    return {(row.period, row.from_ccy, row.to_ccy, row.rate, row.source) for row in rows}


def _assert_costs_match(session: object) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    rows = session.scalars(select(SkuCost)).all()
    signatures = {
        (
            row.internal_sku,
            row.valid_from,
            row.valid_to,
            row.unit_cost,
            row.freight_per_unit,
            row.currency,
        )
        for row in rows
    }
    assert len(signatures) == _data_rows("costs.csv")
    cup = [row for row in rows if row.internal_sku == "INT-CUP-500"]
    assert len(cup) == 2
    by_start = {row.valid_from: row for row in cup}
    assert by_start[_EPOCH].valid_to == _CUP_NEXT
    assert by_start[_CUP_NEXT].valid_to is None
    assert by_start[_EPOCH].unit_cost == Decimal("12.00")
    assert by_start[_CUP_NEXT].unit_cost == Decimal("13.50")


def _assert_rates_match(session: object) -> None:
    found = _fx_signatures(session)
    assert found == {
        ("2026-10", "USD", "CNY", Decimal("7.25000000"), "template_fx_rates"),
        ("2026-10", "EUR", "CNY", Decimal("7.85000000"), "template_fx_rates"),
    }


def _cost_mapping(tmp_path: Path, *, with_end: bool) -> ColumnMapping:
    end = '  valid_to: "结束日期"\n' if with_end else ""
    path = tmp_path / "cost-map.yaml"
    path.write_text(
        f"""
target: sku_cost
source_name: overlap_demo
timezone: UTC
amount_locale: us
date_formats: ["%Y-%m-%d"]
columns:
  internal_sku: "内部SKU"
  unit_cost: "采购单价"
  freight_per_unit: "头程单价"
  currency: "币种"
  valid_from: "生效日期"
{end}""".strip()
        + "\n",
        encoding="utf-8",
    )
    return load_mapping(path)


def _xlsx_rows(path: Path) -> list[list[str]]:
    workbook = CalamineWorkbook.from_path(str(path))
    try:
        sheet = workbook.get_sheet_by_index(0)
        raw_rows = sheet.to_python(skip_empty_area=False)
    finally:
        workbook.close()
    rendered: list[list[str]] = []
    for raw in raw_rows:
        assert isinstance(raw, list | tuple)
        rendered.append(["" if cell is None else str(cell) for cell in raw])
    return rendered
