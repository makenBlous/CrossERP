from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from crosserp.cli import app


def test_demo_check_uses_independent_database(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CROSSERP_DATABASE_URL", raising=False)
    result = CliRunner().invoke(app, ["demo", "--check", "--no-browser"])
    assert result.exit_code == 0, result.output
    assert "匹配率 95.00%" in result.output
    assert (tmp_path / ".crosserp" / "demo.db").is_file()
