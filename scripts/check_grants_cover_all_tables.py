"""检查 MySQL 和 PostgreSQL 授权模板显式覆盖每张业务表。"""

from __future__ import annotations

import re
from pathlib import Path

from crosserp.db.schema import V01_TABLES

ROOT = Path(__file__).resolve().parents[1]
_TABLE_REF = re.compile(r"\b(?:crosserp|public)\.([a-z][a-z0-9_]*)\b", re.I)


def referenced_tables(path: Path) -> set[str]:
    """只读取授权语句里的表名, 不把注释当作授权。"""
    text = re.sub(r"--[^\n]*|#[^\n]*", "", path.read_text(encoding="utf-8"))
    return {match.group(1).lower() for match in _TABLE_REF.finditer(text)}


def missing_tables(path: Path) -> set[str]:
    return set(V01_TABLES) - referenced_tables(path)


def main() -> int:
    failures: list[str] = []
    for name in ("grant_pg.sql", "grant_mysql.sql"):
        path = ROOT / "scripts" / "sql" / name
        missing = sorted(missing_tables(path))
        if missing:
            failures.append(f"{name}: {', '.join(missing)}")
    if failures:
        print("授权脚本缺少表: " + "; ".join(failures))
        return 1
    print(f"授权脚本覆盖 {len(V01_TABLES)} 张业务表")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
