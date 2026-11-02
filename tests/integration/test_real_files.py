"""脱敏真实文件试导入。目录不提交。不存在就跳过。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import downgrade_base

pytestmark = pytest.mark.db

REAL = Path(__file__).resolve().parents[2] / "samples" / "real_anonymized"


def test_real_anonymized_files_do_not_crash(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not REAL.is_dir():
        pytest.skip("samples/real_anonymized/ 不存在")
    files = sorted(path for path in REAL.iterdir() if path.is_file())
    if not files:
        pytest.skip("samples/real_anonymized/ 没有文件")
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    runner = CliRunner()
    try:
        for path in files:
            result = runner.invoke(app, ["import", str(path)], catch_exceptions=False)
            assert result.exit_code in {0, 1}, result.output
            assert result.exc_info is None
    finally:
        downgrade_base(url)
