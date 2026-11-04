"""审计哈希链。追加、篡改、删除和回滚。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.audit.context import AuditContext, audited
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


def test_reason_over_512_is_rejected_and_actor_name_is_stored(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            with pytest.raises(ValueError, match="reason 超过 512"):
                append(
                    session,
                    "system",
                    "config.change",
                    "config",
                    "1",
                    None,
                    {"changed": True},
                    reason="x" * 513,
                )
            row = append(
                session,
                "system",
                "config.change",
                "config",
                "2",
                None,
                {"changed": True},
                actor_name="maken",
            )
            assert row.actor_user_id is None
            assert row.actor_name == "maken"
            assert row.hash_version == 2
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_audited_context_writes_actor_name(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            with audited(
                session,
                AuditContext(actor_type="user", actor_name="maken", request_id="req-1"),
                action="config.change",
                target_type="config",
                target_id="demo",
                before={"enabled": False},
                after={"enabled": True},
            ):
                pass
            row = session.scalar(select(AuditLog).where(AuditLog.action == "config.change"))
            assert row is not None
            assert row.actor_name == "maken"
            assert row.request_id == "req-1"
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_audited_append_failure_rolls_back_business_change(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        from crosserp.audit import context as audit_context

        def fail_append(*args: object, **kwargs: object) -> None:
            raise RuntimeError("模拟审计失败")

        monkeypatch.setattr(audit_context, "append", fail_append)
        with pytest.raises(RuntimeError, match="模拟审计失败"), session_scope(engine) as session:
            row = AuditLog(
                id=uuid4(),
                seq=1,
                ts=datetime.now(UTC),
                actor_type="system",
                actor_user_id=None,
                actor_name="system",
                actor_role=None,
                action="config.change",
                target_type="config",
                target_id="rollback",
                before_json={"enabled": False},
                after_json={"enabled": True},
                approval_id=None,
                approver_id=None,
                reason=None,
                request_id=None,
                ip=None,
                user_agent=None,
                self_approved=False,
                prev_hash="0" * 64,
                hash="0" * 64,
                hash_version=2,
            )
            session.add(row)
            with audit_context.audited(
                session,
                AuditContext(actor_name="maken"),
                action="config.change",
                target_type="config",
                target_id="rollback",
                before=None,
                after={"enabled": True},
            ):
                session.flush()
        with session_scope(engine) as session:
            assert session.scalar(select(AuditLog).where(AuditLog.target_id == "rollback")) is None
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
