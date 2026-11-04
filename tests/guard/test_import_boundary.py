"""只有唯一写出口可以依赖 ledger.targets。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard


def test_ledger_target_imports_are_inside_write_service() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "crosserp"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        allowed = relative == "ledger/write_service.py" or relative.startswith("ledger/targets/")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module: str | None = None
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("crosserp.ledger.targets"):
                        module = item.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("crosserp.ledger.targets"):
                    module = node.module
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("crosserp.ledger.targets")
            ):
                module = node.value
            if module is not None and not allowed:
                violations.append(f"{relative}: {module}")
    assert violations == []
