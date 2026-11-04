"""审计导出和检查点集成测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from crosserp.audit.log import append
from crosserp.cli import app
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db


def test_audit_export_cli_roundtrip(
    engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            append(
                session,
                "system",
                "import",
                "batch",
                "1",
                None,
                {"n": 1},
                ts=datetime(2026, 11, 4, 1, tzinfo=UTC),
            )
        monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
        output = tmp_path / "audit.zip"
        exported = CliRunner().invoke(
            app,
            [
                "audit",
                "export",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-30",
                "--format",
                "jsonl",
                "--out",
                str(output),
            ],
        )
        assert exported.exit_code == 0, exported.output
        verified = CliRunner().invoke(app, ["audit", "verify-export", str(output)])
        assert verified.exit_code == 0, verified.output
    finally:
        downgrade_base(url)
