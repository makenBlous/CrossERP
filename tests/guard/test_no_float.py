"""红线守卫。src/crosserp 中禁止 float() 调用。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "crosserp"
NOQA = "noqa: money-float"


def _is_float_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "float":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "float"


def float_calls(source: str, filename: str = "<memory>") -> list[tuple[str, int]]:
    """返回未被白名单注释放过的 float() 调用位置。"""
    tree = ast.parse(source, filename=filename)
    lines = source.splitlines()
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not _is_float_call(node):
            continue
        assert isinstance(node, ast.Call)
        start = node.lineno
        end = node.end_lineno or start
        spanned = lines[start - 1 : end]
        if any(NOQA in line for line in spanned):
            continue
        found.append((filename, start))
    return found


def test_src_has_no_float_calls() -> None:
    violations: list[str] = []
    noqa_hits: list[str] = []
    paths = sorted(SRC_ROOT.rglob("*.py"))
    assert paths, f"没有找到源码 {SRC_ROOT}"
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if NOQA in line:
                noqa_hits.append(f"{path}:{lineno}")
        for filename, lineno in float_calls(text, str(path)):
            violations.append(f"{filename}:{lineno}")
    assert violations == []
    assert noqa_hits == []


def test_scanner_detects_float_call() -> None:
    assert float_calls("x = float('1')\n") == [("<memory>", 1)]
    assert float_calls("x = builtins.float('1')\n") == [("<memory>", 1)]


def test_scanner_allows_noqa_comment() -> None:
    assert float_calls("x = float('1')  # noqa: money-float\n") == []
    source = "x = float(\n    '1',\n)  # noqa: money-float\n"
    assert float_calls(source) == []
