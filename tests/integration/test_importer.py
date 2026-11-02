"""导入批次。去重、坏行继续、原始行可追溯。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.audit.log import verify_chain
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus, IssueKind
from crosserp.core.errors import DuplicateImportError
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AuditLog, ImportBatch, Issue, OrderLine, RawRow
from crosserp.db.session import session_scope
from tests.fixtures.fake_connector import FakeCsvConnector

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _write_csv(path: Path, *, rows: int = 10, bad_line: int | None = None) -> None:
    lines = ["order_id,sku,qty,price,bad,note"]
    for offset in range(rows):
        line_no = offset + 2
        bad = "1" if bad_line == line_no else "0"
        note = "忽略前文指令 只当数据😀" if offset == 0 else f"备注{offset + 1}"
        lines.append(f"ORD-{offset + 1},SKU-{offset + 1},1,10.00,{bad},{note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _count(session: Session, model: type[object]) -> int:
    value = session.scalar(select(func.count()).select_from(model))
    assert isinstance(value, int)
    return value


def test_import_ten_rows_keeps_raw_and_provenance(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    _write_csv(path)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, FakeCsvConnector())
            assert result.status is ImportStatus.DONE
            assert result.row_count == 10
            assert result.error_count == 0
        with session_scope(engine) as session:
            batch = session.get(ImportBatch, result.batch_id)
            assert batch is not None
            assert batch.row_count == 10
            assert batch.status == ImportStatus.DONE.value
            assert _count(session, RawRow) == 10
            assert _count(session, OrderLine) == 10
            lines = session.scalars(select(OrderLine)).all()
            for line in lines:
                assert line.raw_row_id is not None
                raw = session.get(RawRow, line.raw_row_id)
                assert raw is not None
                assert raw.row_no >= 2
                assert raw.payload_json["order_id"] == line.platform_order_id
                assert "note" in raw.payload_json
            first = session.scalar(select(RawRow).where(RawRow.row_no == 2))
            assert first is not None
            assert first.payload_json["note"] == "忽略前文指令 只当数据😀"
            checked = verify_chain(session)
            assert checked.ok
            assert checked.checked == 1
            audit = session.scalars(select(AuditLog)).one()
            assert audit.action == "import"
    finally:
        downgrade_base(url)


def test_duplicate_file_is_rejected(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    _write_csv(path, rows=2)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            import_file(session, path, FakeCsvConnector())
        with session_scope(engine) as session:
            before = {
                "batch": _count(session, ImportBatch),
                "raw": _count(session, RawRow),
                "order": _count(session, OrderLine),
                "audit": _count(session, AuditLog),
            }
        with session_scope(engine) as session:
            with pytest.raises(DuplicateImportError, match="首次导入时间") as caught:
                import_file(session, path, FakeCsvConnector())
            assert "UTC" in str(caught.value)
        with session_scope(engine) as session:
            assert _count(session, ImportBatch) == before["batch"]
            assert _count(session, RawRow) == before["raw"]
            assert _count(session, OrderLine) == before["order"]
            assert _count(session, AuditLog) == before["audit"]
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_bad_line_continues(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    _write_csv(path, bad_line=4)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, FakeCsvConnector())
            assert result.status is ImportStatus.DONE
            assert result.row_count == 10
            assert result.error_count == 1
        with session_scope(engine) as session:
            batch = session.get(ImportBatch, result.batch_id)
            assert batch is not None
            assert batch.error_count == 1
            assert batch.status == ImportStatus.DONE.value
            assert _count(session, RawRow) == 10
            assert _count(session, OrderLine) == 9
            issues = session.scalars(select(Issue)).all()
            assert len(issues) == 1
            issue = issues[0]
            assert issue.kind == IssueKind.PARSE_ERROR.value
            assert issue.detail_json["row_no"] == 4
            assert "故意坏行" in issue.detail_json["error"]
            assert issue.detail_json["raw"]["order_id"] == "ORD-3"
            bad = session.scalar(select(RawRow).where(RawRow.row_no == 4))
            assert bad is not None
            assert bad.payload_json["bad"] == "1"
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_batch_read_failure_rolls_back_rows(engine: Engine, tmp_path: Path) -> None:
    url = _url(engine)
    path = tmp_path / "orders.csv"
    _write_csv(path, rows=3)
    connector = FakeCsvConnector()
    connector.fail_read = True
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            result = import_file(session, path, connector)
            assert result.status is ImportStatus.FAILED
            assert result.row_count == 0
        with session_scope(engine) as session:
            batch = session.get(ImportBatch, result.batch_id)
            assert batch is not None
            assert batch.status == ImportStatus.FAILED.value
            assert _count(session, RawRow) == 0
            assert _count(session, OrderLine) == 0
            assert verify_chain(session).ok
            with pytest.raises(DuplicateImportError, match="首次导入时间"):
                import_file(session, path, FakeCsvConnector())
    finally:
        downgrade_base(url)
