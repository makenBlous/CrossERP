"""空包冒烟测试。"""

from __future__ import annotations

from typer.testing import CliRunner

import crosserp
from crosserp.cli import app


def test_package_version() -> None:
    assert crosserp.__version__ == "0.0.1"
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.0.1"
