"""三库差异。当前只做启动自检。不做 upsert。"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from crosserp.core.errors import DatabaseConfigError

_VERSION_RE = re.compile(r"(\d+)\.(\d+)")
_SAFE_DB_NAME_RE = re.compile(r"[A-Za-z0-9_]+")
_MYSQL_MIN = (8, 4)
_POSTGRES_MIN = (18, 0)


@dataclass(frozen=True)
class ServerStatus:
    """启动自检通过后的数据库概况。"""

    dialect: str
    version: str
    charset: str | None = None
    strict_trans_tables: bool | None = None


def parse_server_version(version: str) -> tuple[int, int] | None:
    """取主版本和次版本。解析不了返回 None。"""
    match = _VERSION_RE.search(version)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _alter_database_sql(database: str) -> str:
    name = database if _SAFE_DB_NAME_RE.fullmatch(database) else "crosserp"
    return f"ALTER DATABASE {name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"


def mysql_config_error(
    version: str,
    charset: str | None,
    sql_mode: str | None,
    database: str,
) -> str | None:
    """MySQL 配置不合格时返回中文修复说明。合格返回 None。"""
    problems: list[str] = []
    parsed = parse_server_version(version)
    if parsed is None or parsed < _MYSQL_MIN:
        problems.append(
            f"MySQL 版本必须 >= 8.4。当前为 {version}。请升级到 MySQL 8.4 LTS。不支持 MySQL 8.0。"
        )
    shown_charset = (charset or "").strip()
    if shown_charset.casefold() != "utf8mb4":
        label = shown_charset or "(空)"
        problems.append(
            f"当前数据库字符集为 {label}。必须是 utf8mb4。请执行 {_alter_database_sql(database)}"
        )
    modes = {part.strip().upper() for part in (sql_mode or "").split(",") if part.strip()}
    if "STRICT_TRANS_TABLES" not in modes:
        shown_mode = (sql_mode or "").strip() or "(空)"
        problems.append(
            f"当前 sql_mode 为 {shown_mode}。必须包含 STRICT_TRANS_TABLES。"
            "请在服务器配置中加入 STRICT_TRANS_TABLES 后重启。"
            "或执行 SET GLOBAL sql_mode = CONCAT(@@sql_mode, ',STRICT_TRANS_TABLES');"
        )
    if not problems:
        return None
    return "MySQL 启动自检失败。\n" + "\n".join(problems)


def postgres_version_warning(version: str) -> str | None:
    """低于 18 时返回警告文本。不拒绝启动。"""
    parsed = parse_server_version(version)
    if parsed is not None and parsed >= _POSTGRES_MIN:
        return None
    shown = version.strip() or "(未知)"
    return f"PostgreSQL 版本 {shown} 低于 18。建议升级到 PostgreSQL 18。当前仅警告。不拒绝启动。"


def _required_text(conn: Connection, sql: str) -> str:
    value = conn.execute(text(sql)).scalar_one()
    if value is None:
        raise DatabaseConfigError(f"数据库未返回自检结果: {sql}")
    return str(value)


def check_server(engine: Engine) -> ServerStatus:
    """启动自检。MySQL 不合格抛 DatabaseConfigError。PostgreSQL 低于 18 只警告。"""
    dialect_name = engine.dialect.name
    with engine.connect() as conn:
        if dialect_name == "mysql":
            version = _required_text(conn, "SELECT VERSION()")
            charset = _required_text(conn, "SELECT @@character_set_database").strip()
            sql_mode = _required_text(conn, "SELECT @@sql_mode")
            database = engine.url.database or "crosserp"
            message = mysql_config_error(version, charset, sql_mode, database)
            if message is not None:
                raise DatabaseConfigError(message)
            return ServerStatus(
                dialect="mysql",
                version=version,
                charset=charset,
                strict_trans_tables=True,
            )
        if dialect_name == "postgresql":
            version = _required_text(conn, "SHOW server_version")
            warning = postgres_version_warning(version)
            if warning is not None:
                warnings.warn(warning, UserWarning, stacklevel=2)
            return ServerStatus(dialect="postgresql", version=version)
        if dialect_name == "sqlite":
            version = _required_text(conn, "SELECT sqlite_version()")
            return ServerStatus(dialect="sqlite", version=version)
    raise DatabaseConfigError(f"不支持的数据库类型: {dialect_name}")
