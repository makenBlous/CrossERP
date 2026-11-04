"""不满足审批条件时，唯一写出口必须拒绝并留下审计。"""  # noqa: RUF002

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from crosserp.approval.service import approve, create, reject, submit
from crosserp.approval.state import ApprovalState
from crosserp.audit.log import verify_chain
from crosserp.cli import app
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Approval, AuditLog, ExportArtifact, ProfitSnapshot, Store
from crosserp.db.session import session_scope, sqlite_file_url
from crosserp.ledger.write_service import ApprovalRequired, export

pytestmark = [pytest.mark.guard, pytest.mark.db]


def _report(session: Session, *, store_name: str = "guard-store") -> tuple[str, str]:
    store = Store(id=uuid4(), platform="amazon", marketplace="US", name=store_name, currency="USD")
    session.add(store)
    session.flush()
    snapshot = ProfitSnapshot(
        id=uuid4(),
        period="2026-10",
        internal_sku="SKU-1",
        store_id=store.id,
        revenue=Decimal("10.0000"),
        fees=Decimal("1.0000"),
        refunds=Decimal("0.0000"),
        cogs=Decimal("2.0000"),
        freight=Decimal("0.0000"),
        ads=None,
        profit=Decimal("7.0000"),
        currency="USD",
        calc_version="0.1.0",
        inputs_hash="a" * 64,
        qty_sold=1,
        qty_refunded=0,
        qty_net=1,
        promotion=Decimal("0.0000"),
        fx_rate=None,
        profit_cny=None,
        ads_included=False,
        status="ok",
        recon_run_id=None,
    )
    session.add(snapshot)
    session.flush()
    batch = f"profit_report:{store_name}:2026-10"
    payload = hashlib.sha256(("a" * 64).encode("ascii")).hexdigest()
    return batch, payload


def test_four_denials_leave_audit_and_no_artifact(engine: Engine, tmp_path: Path) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        batch = "profit_report:missing-store:2026-10"
        with session_scope(engine) as session:
            for token in (None, "bad-token"):
                with pytest.raises(ApprovalRequired):
                    export(session, batch, "xlsx", token, output_dir=tmp_path)
        with session_scope(engine) as session:
            row = create(
                session,
                target_type="profit_report",
                target_id="missing-store:2026-10",
                requested_by="operator",
            )
            submit(session, row, actor="operator")
            reject(session, row, approver="finance", comment="不允许导出")
        with session_scope(engine) as session:
            with pytest.raises(ApprovalRequired):
                export(session, batch, "xlsx", "bad-token", output_dir=tmp_path)
            row = session.scalar(
                select(Approval).where(Approval.target_id == "missing-store:2026-10")
            )
            assert row is not None
            assert row.state == ApprovalState.REJECTED.value
            assert session.scalar(select(ExportArtifact.id)) is None
            denied = list(
                session.scalars(select(AuditLog).where(AuditLog.action == "ledger.export_denied"))
            )
            assert len(denied) == 3
            assert all(item.reason for item in denied)
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_approved_export_can_only_be_used_once(engine: Engine, tmp_path: Path) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            batch, payload = _report(session)
        with session_scope(engine) as session:
            row = create(
                session,
                target_type="profit_report",
                target_id="guard-store:2026-10",
                requested_by="operator",
                payload_hash=payload,
                requested_at=datetime(2026, 11, 4, tzinfo=UTC),
            )
            submit(session, row, actor="operator")
            token = approve(session, row, approver="finance")
        with session_scope(engine) as session:
            artifact = export(session, batch, "xlsx", token, output_dir=tmp_path)
            assert Path(artifact.file_path or "").is_file()
            artifact_id = artifact.id
        with session_scope(engine) as session:
            with pytest.raises(ApprovalRequired, match="已被使用"):
                export(session, batch, "xlsx", token, output_dir=tmp_path)
            assert session.scalar(select(ExportArtifact.id)) == artifact_id
            actions = list(session.scalars(select(AuditLog.action).order_by(AuditLog.seq)))
            assert "ledger.export" in actions
            assert "ledger.export_denied" in actions
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_cli_export_without_token_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CROSSERP_DATABASE_URL", sqlite_file_url(tmp_path / "cli.db"))
    result = CliRunner().invoke(
        app,
        [
            "export",
            "--target",
            "xlsx",
            "--batch",
            "profit_report:store:2026-10",
        ],
    )
    assert result.exit_code == 1
    assert "没有有效审批" in result.output
