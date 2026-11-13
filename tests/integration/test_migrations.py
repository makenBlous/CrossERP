"""迁移往返。upgrade head → 当前业务表 → downgrade base → 再 upgrade。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import check_schema, downgrade_base, upgrade_head
from crosserp.db.schema import V01_TABLES, ImportBatch, RawRow
from crosserp.db.session import session_scope, sqlite_file_url

pytestmark = pytest.mark.db

_EXPECTED_COUNT = 74  # 72 张表现有表加上 user_store_grant 与 agent_store_scope


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _business_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_v01_table_count() -> None:
    assert len(V01_TABLES) == _EXPECTED_COUNT


def test_migration_roundtrip(engine: Engine) -> None:
    url = _url(engine)
    try:
        upgrade_head(url)
        assert _business_tables(engine) == set(V01_TABLES)
        downgrade_base(url)
        assert _business_tables(engine) == set()
        upgrade_head(url)
        assert _business_tables(engine) == set(V01_TABLES)
        check_schema(url)
    finally:
        downgrade_base(url)


def test_sqlite_money_column_is_integer(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        pytest.skip("只在 SQLite 检查万分位整数列")
    url = _url(engine)
    try:
        upgrade_head(url)
        with engine.connect() as conn:
            rows = conn.exec_driver_sql("PRAGMA table_info(settlement)").all()
            fx_rows = conn.exec_driver_sql("PRAGMA table_info(fx_rate)").all()
        total = next(row for row in rows if row[1] == "total")
        rate = next(row for row in fx_rows if row[1] == "rate")
        assert str(total[2]).upper() in {"BIGINT", "INTEGER"}
        assert "CHAR" in str(rate[2]).upper() or "VARCHAR" in str(rate[2]).upper()
    finally:
        downgrade_base(url)


def test_raw_row_autoincrement(engine: Engine) -> None:
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            batch = ImportBatch(
                connector_id="fake",
                connector_version="0",
                file_name="sample.csv",
                file_sha256="a" * 64,
                imported_at=datetime(2026, 11, 2, tzinfo=UTC),
                row_count=1,
                status="running",
                error_count=0,
            )
            session.add(batch)
            session.flush()
            row = RawRow(batch_id=batch.id, row_no=1, payload_json={"sku": "保温杯"})
            session.add(row)
            session.flush()
            assert isinstance(row.id, int)
            assert row.id >= 1
    finally:
        downgrade_base(url)


def test_import_batch_counts_json_is_non_null_with_stage_defaults(engine: Engine) -> None:
    url = _url(engine)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            batch = ImportBatch(
                connector_id="counts",
                connector_version="1",
                file_name="counts.csv",
                file_sha256="d" * 64,
                imported_at=datetime(2026, 11, 2, tzinfo=UTC),
                row_count=0,
                status="uploaded",
                error_count=0,
            )
            session.add(batch)
            session.flush()
            assert batch.counts_json == {
                "landed": 0,
                "valid": 0,
                "duplicate": 0,
                "quarantined": 0,
                "projected": 0,
            }
            counts_column = next(
                column
                for column in inspect(engine).get_columns("import_batch")
                if column["name"] == "counts_json"
            )
            assert counts_column["nullable"] is False
    finally:
        downgrade_base(url)


def test_init_cli_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "nested" / "data.db"
    monkeypatch.setenv("CROSSERP_DATABASE_URL", sqlite_file_url(database))
    runner = CliRunner()
    first = runner.invoke(app, ["init"])
    assert first.exit_code == 0, first.output
    assert "数据库已就绪" in first.output
    assert database.is_file()
    second = runner.invoke(app, ["init"])
    assert second.exit_code == 0, second.output
    assert "数据库已就绪" in second.output
