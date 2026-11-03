"""T15 导入批次状态、重试和人工收尾。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus
from crosserp.core.errors import ImportInProgressError
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.imports import insert_import_batch
from crosserp.db.schema import AuditLog, ImportBatch
from crosserp.db.session import session_scope
from tests.fixtures.fake_connector import FakeCsvConnector

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_running_batch_requires_manual_mark_failed(
    engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    path.write_text("order_id,sku,qty,price\nORD-1,SKU-1,1,10.00\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            batch = insert_import_batch(
                session,
                connector_id="fake.csv",
                connector_version="1",
                file_name=path.name,
                file_sha256=digest,
                imported_at=datetime.now(UTC),
            )
            batch_id = batch.id

        with (
            session_scope(engine) as session,
            pytest.raises(ImportInProgressError, match="mark-failed"),
        ):
            import_file(session, path, FakeCsvConnector())

        monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
        marked = CliRunner().invoke(app, ["import", "--mark-failed", str(batch_id)])
        assert marked.exit_code == 0, marked.output
        listed = CliRunner().invoke(app, ["imports", "list"])
        assert listed.exit_code == 0, listed.output
        assert "MANUAL_MARK_FAILED" not in listed.output
        with session_scope(engine) as session:
            row = session.get(ImportBatch, batch_id)
            assert row is not None
            assert row.status == ImportStatus.FAILED.value
            assert row.failure_code == "MANUAL_MARK_FAILED"
            assert session.scalar(
                select(AuditLog.action).where(AuditLog.target_id == str(batch_id))
            ) == ("import_failed")
    finally:
        downgrade_base(url)


def test_cli_auto_missing_file_records_failed_batch(
    engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(engine)
    missing = tmp_path / "does-not-exist.csv"
    try:
        upgrade_head(url)
        monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
        result = CliRunner().invoke(app, ["import", str(missing)])
        assert result.exit_code == 1, result.output
        listed = CliRunner().invoke(app, ["imports", "list"])
        assert listed.exit_code == 0, listed.output
        assert "does-not-exist.csv" in listed.output
        assert "失败" in listed.output
        with session_scope(engine) as session:
            batch = session.scalar(select(ImportBatch).where(ImportBatch.file_name == missing.name))
            assert batch is not None
            assert batch.file_sha256 is None
            assert batch.failure_code == "FILE_UNREADABLE"
            assert batch.failure_reason is not None
    finally:
        downgrade_base(url)
