"""审计哈希链。追加、篡改、删除和回滚。"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.audit.log import append, verify_chain
from crosserp.cli import app
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AuditHead, AuditLog
from crosserp.db.session import session_scope, sqlite_file_url

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _append_five(engine: Engine) -> list[str]:
    ids: list[str] = []
    with session_scope(engine) as session:
        for index in range(5):
            row = append(
                session,
                "system",
                "import",
                "batch",
                str(index + 1),
                None,
                {"n": index, "name": "保温杯"},
            )
            ids.append(str(row.id))
    return ids


def test_append_five_verifies(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        _append_five(engine)
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is True
        assert result.checked == 5
        assert result.first_bad_id is None
        assert result.reason is None
    finally:
        downgrade_base(url)


def test_sql_tamper_after_json_points_at_third_row(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        ids = _append_five(engine)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE audit_log SET after_json = :payload WHERE seq = :seq"),
                {"payload": '{"tampered":true}', "seq": 3},
            )
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is False
        assert result.first_bad_id == ids[2]
    finally:
        downgrade_base(url)


def test_delete_second_row_fails(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        _append_five(engine)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM audit_log WHERE seq = :seq"), {"seq": 2})
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is False
        assert result.first_bad_id is not None
    finally:
        downgrade_base(url)


def test_delete_last_row_fails(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        ids = _append_five(engine)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM audit_log WHERE seq = :seq"), {"seq": 5})
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is False
        assert result.first_bad_id == ids[4]
    finally:
        downgrade_base(url)


def test_rollback_removes_audit_rows(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with pytest.raises(RuntimeError, match="回滚"), session_scope(engine) as session:
            append(session, "system", "import", "batch", "1", None, {"n": 1})
            raise RuntimeError("回滚")
        with session_scope(engine) as session:
            result = verify_chain(session)
            log_count = session.scalar(select(func.count()).select_from(AuditLog))
            head_count = session.scalar(select(func.count()).select_from(AuditHead))
        assert result.ok is True
        assert result.checked == 0
        assert log_count == 0
        assert head_count == 0
    finally:
        downgrade_base(url)


def test_optional_fields_stay_in_chain(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            append(
                session,
                "user",
                "update",
                "sku_cost",
                "sku-1",
                {"unit_cost": "10.50"},
                {"unit_cost": "11.00"},
                actor_user_id=uuid4(),
                actor_role="owner",
                approval_id=uuid4(),
                approver_id=uuid4(),
                reason="更正成本",
                request_id="req-1",
                ip="203.0.113.8",
                user_agent="pytest",
                self_approved=False,
            )
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is True
        assert result.checked == 1
    finally:
        downgrade_base(url)


def test_cli_verify_empty_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CROSSERP_DATABASE_URL", sqlite_file_url(tmp_path / "empty.db"))
    result = CliRunner().invoke(app, ["audit", "verify"])
    assert result.exit_code == 0, result.output
    assert "审计链完整：0 条" in result.stdout  # noqa: RUF001


def test_cli_verify_failure_exits_1(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    upgrade_head(url)
    try:
        ids = _append_five(engine)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE audit_log SET reason = :reason WHERE seq = :seq"),
                {"reason": "被改过", "seq": 3},
            )
        result = CliRunner().invoke(app, ["audit", "verify"])
        assert result.exit_code == 1
        assert ids[2] in result.output
        assert "第一条坏记录" in result.output
    finally:
        downgrade_base(url)
