"""离线检查 Markdown 中指向仓库文件的相对链接。"""

from __future__ import annotations

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


def main() -> int:
    missing: list[str] = []
    for markdown in ROOT.rglob("*.md"):
        if markdown.name == "README_追加.md" or any(
            part in EXCLUDED_DIRS for part in markdown.parts
        ):
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
