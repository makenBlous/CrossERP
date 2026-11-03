"""Profit golden comparison and reference independence."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import downgrade_base
from crosserp.db.schema import ProfitSnapshot
from crosserp.db.session import session_scope
from crosserp.profit.golden import compare_profit_csv

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[2]


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_synthetic_profit_golden_is_exact(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    try:
        assert CliRunner().invoke(app, ["init"]).exit_code == 0
        assert CliRunner().invoke(app, ["demo-import"]).exit_code == 0
        assert CliRunner().invoke(app, ["reconcile", "--period", "2026-10"]).exit_code == 0
        assert CliRunner().invoke(app, ["profit", "--period", "2026-10"]).exit_code == 0
        with session_scope(engine) as session:
            result = compare_profit_csv(
                session, "2026-10", ROOT / "tests" / "golden" / "profit_expected.csv"
            )
            assert result.ok
            assert result.matched_rows == 8
            assert result.reference_only_rows == 12
    finally:
        with session_scope(engine) as session:
            session.execute(delete(ProfitSnapshot))
        downgrade_base(url)


def test_reference_script_does_not_import_profit_implementation() -> None:
    tree = ast.parse((ROOT / "scripts" / "gen_samples.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "crosserp.profit" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "crosserp.profit"


def test_golden_reports_a_one_cent_difference(
    tmp_path: Path, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = ROOT / "tests" / "golden" / "profit_expected.csv"
    changed = tmp_path / "changed.csv"
    changed.write_text(
        source.read_text(encoding="utf-8").replace(",440.55,", ",440.56,", 1),
        encoding="utf-8",
    )
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    try:
        assert CliRunner().invoke(app, ["init"]).exit_code == 0
        assert CliRunner().invoke(app, ["demo-import"]).exit_code == 0
        assert CliRunner().invoke(app, ["reconcile", "--period", "2026-10"]).exit_code == 0
        assert CliRunner().invoke(app, ["profit", "--period", "2026-10"]).exit_code == 0
        with session_scope(engine) as session:
            result = compare_profit_csv(session, "2026-10", changed)
            assert not result.ok
            assert any(diff.column == "profit" for diff in result.diffs)
    finally:
        with session_scope(engine) as session:
            session.execute(delete(ProfitSnapshot))
        downgrade_base(url)
