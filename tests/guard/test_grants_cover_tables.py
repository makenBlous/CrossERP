"""授权脚本必须覆盖声明式模型中的每张业务表。"""

from __future__ import annotations

from pathlib import Path

from scripts.check_grants_cover_all_tables import missing_tables

ROOT = Path(__file__).resolve().parents[2]


def test_postgres_grants_cover_all_tables() -> None:
    assert missing_tables(ROOT / "scripts" / "sql" / "grant_pg.sql") == set()


def test_mysql_grants_cover_all_tables() -> None:
    assert missing_tables(ROOT / "scripts" / "sql" / "grant_mysql.sql") == set()
