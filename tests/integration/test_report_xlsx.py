"""Read-back checks for the human report."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import delete
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import downgrade_base
from crosserp.db.schema import ProfitSnapshot
from crosserp.db.session import get_database_url, make_engine, session_scope

pytestmark = pytest.mark.db


def test_profit_report_xlsx_has_three_readable_sheets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "report.sqlite"
    monkeypatch.setenv("CROSSERP_DATABASE_URL", f"sqlite:///{database}")
    path = tmp_path / "report.xlsx"
    assert CliRunner().invoke(app, ["init"]).exit_code == 0
    assert CliRunner().invoke(app, ["demo-import"]).exit_code == 0
    result = CliRunner().invoke(app, ["profit", "--period", "2026-10", "--out", str(path)])
    assert result.exit_code == 0, result.output
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    assert workbook.sheetnames == ["SKU利润", "异常清单", "说明"]
    assert workbook["SKU利润"].cell(1, 1).value == "期间"
    assert workbook["说明"].cell(4, 2).value is not None
    assert "未含广告" in str(workbook["说明"].cell(4, 2).value)
    second = CliRunner().invoke(app, ["profit", "--period", "2026-10", "--out", str(path)])
    assert second.exit_code == 1
    assert "已存在" in second.output
    with session_scope(make_engine(get_database_url())) as session:
        session.execute(delete(ProfitSnapshot))
    downgrade_base(get_database_url())
