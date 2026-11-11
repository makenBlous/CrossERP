"""离线检查 Markdown 中指向仓库文件的相对链接。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".ci",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
}


def iter_markdown():
    """遍历阶段即剪掉依赖/生成目录, 避免进入 node_modules 等。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                yield Path(dirpath) / name


def main() -> int:
    missing: list[str] = []
    for markdown in iter_markdown():
        if markdown.name == "README_追加.md":
            continue
        for raw in LINK.findall(markdown.read_text(encoding="utf-8")):
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(urlsplit(raw).path)
            if not target or target.startswith("#"):
                continue
            candidate = (markdown.parent / target).resolve()
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                missing.append(f"{markdown.relative_to(ROOT)} -> {raw}")
                continue
            if not candidate.exists():
                missing.append(f"{markdown.relative_to(ROOT)} -> {raw}")
    if missing:
        print("坏链接:")
        print("\n".join(missing))
        return 1
    print("文档相对链接完整")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
