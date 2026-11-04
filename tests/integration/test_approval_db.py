"""审批服务的 SQLite 和事务行为。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from crosserp.approval.service import (
    approve,
    check_fresh,
    create,
    reject,
    reopen,
    submit,
    token_matches,
)
from crosserp.approval.state import ApprovalState, ConcurrentModification, IllegalTransition
from crosserp.audit.log import verify_chain
from crosserp.cli import app
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Approval, AuditLog
from crosserp.db.session import session_scope, sqlite_file_url

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_approval_lifecycle_hash_invalidation_and_audit(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = create(
                session,
                target_type="profit_report",
                target_id="shop-1:2026-10",
                requested_by="maken",
                payload_hash="a" * 64,
                requested_at=datetime(2026, 11, 4, tzinfo=UTC),
            )
            submit(session, row, actor="maken")
            token = approve(session, row, approver="maken")
            approval_id = row.id
            assert row.state == ApprovalState.APPROVED.value
            assert token_matches(row, token)
            assert row.token_hash != token
            assert check_fresh(session, row, "a" * 64)
            assert check_fresh(session, row, "b" * 64) is False
            assert row.state == ApprovalState.PENDING.value
            assert not token_matches(row, token)
            assert row.token_hash is None
            actions = list(
                session.scalars(
                    select(AuditLog.action)
                    .where(AuditLog.approval_id == approval_id)
                    .order_by(AuditLog.seq)
                )
            )
            assert actions == [
                "approval.create",
                "approval.submit",
                "approval.approve",
                "approval.invalidate",
            ]
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_reject_requires_comment_and_reopen(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = create(
                session,
                target_type="mapping",
                target_id="mapping-1",
                requested_by="operator",
            )
            submit(session, row, actor="operator")
            with pytest.raises(ValueError, match="驳回必须填写原因"):
                reject(session, row, approver="finance", comment=" ")
            reject(session, row, approver="finance", comment="字段对不上")
            assert row.state == ApprovalState.REJECTED.value
            reopen(session, row, actor="operator")
            assert row.state == ApprovalState.DRAFT.value
            assert row.payload_hash is None
            with pytest.raises(IllegalTransition):
                approve(session, row, approver="finance")
    finally:
        downgrade_base(url)


def test_optimistic_lock_rejects_stale_update(engine: Engine) -> None:
    url = _url(engine)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            created = create(
                session,
                target_type="mapping",
                target_id="mapping-2",
                requested_by="operator",
            )
            approval_id = created.id
        left = Session(engine)
        right = Session(engine)
        try:
            left_row = left.get(Approval, approval_id)
            right_row = right.get(Approval, approval_id)
            assert left_row is not None and right_row is not None
            submit(right, right_row, actor="operator")
            right.commit()
            with pytest.raises(ConcurrentModification):
                submit(left, left_row, actor="operator")
            left.rollback()
        finally:
            left.close()
            right.close()
    finally:
        downgrade_base(url)


def test_cli_request_approve_and_reject_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "approval.db"
    monkeypatch.setenv("CROSSERP_DATABASE_URL", sqlite_file_url(database))
    first = CliRunner().invoke(
        app,
        [
            "approval",
            "request",
            "--target",
            "mapping:m-1",
            "--as",
            "operator",
            "--payload-hash",
            "a" * 64,
        ],
    )
    assert first.exit_code == 0, first.output
    approval_id = first.output.split("：", 1)[1].split("（", 1)[0]  # noqa: RUF001
    bad = CliRunner().invoke(app, ["approval", "reject", approval_id, "--as", "finance"])
    assert bad.exit_code == 1
    assert "驳回必须填写原因" in bad.output
    approved = CliRunner().invoke(app, ["approval", "approve", approval_id, "--as", "finance"])
    assert approved.exit_code == 0, approved.output
    assert "一次性 token" in approved.output
