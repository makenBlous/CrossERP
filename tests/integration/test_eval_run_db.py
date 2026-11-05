"""T51 评测结果写入数据库。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.schema import EvalRun
from crosserp.db.session import sqlite_file_url

pytestmark = pytest.mark.db


def test_eval_run_save_persists_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "eval.db"
    monkeypatch.setenv("CROSSERP_DATABASE_URL", sqlite_file_url(database))

    result = CliRunner().invoke(app, ["eval", "run", "--model", "test", "--save"])
    assert result.exit_code == 0, result.output
    assert "评测结果已写入 eval_run" in result.output

    from crosserp.db.session import make_engine, session_scope

    engine = make_engine(sqlite_file_url(database))
    try:
        with session_scope(engine) as session:
            row = session.scalar(select(EvalRun))
            assert row is not None
            assert row.model == "test"
            assert row.total == 20
            assert row.passed == 20
            assert len(row.git_sha) == 40
            assert row.details_json["passed"] == 20
    finally:
        engine.dispose()
