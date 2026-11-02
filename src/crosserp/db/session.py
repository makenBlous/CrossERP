"""数据库连接与会话。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from crosserp.core.errors import DatabaseConfigError

_MYSQL_CHARSET = "utf8mb4"


def sqlite_file_url(path: Path) -> str:
    """生成 Windows 也能打开的 SQLite URL。不手拼反斜杠。"""
    resolved = path.resolve()
    return URL.create(drivername="sqlite", database=str(resolved)).render_as_string(
        hide_password=False
    )


def _load_env_file() -> None:
    """读取当前目录的 `.env`。已有环境变量不覆盖。"""
    path = Path.cwd() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def get_database_url() -> str:
    """读配置文件或环境变量里的 CROSSERP_DATABASE_URL。未设置时用 ~/.crosserp/data.db。"""
    _load_env_file()
    configured = os.environ.get("CROSSERP_DATABASE_URL", "").strip()
    if configured:
        return configured
    path = Path.home() / ".crosserp" / "data.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite_file_url(path)


def _query_param(url: URL, key: str) -> str | None:
    value = url.query.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, tuple) and value and isinstance(value[-1], str):
        return value[-1]
    return None


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def make_engine(url: str) -> Engine:
    """创建引擎。SQLite 打开外键。MySQL URL 没有 charset=utf8mb4 就拒绝。"""
    sa_url = make_url(url)
    backend = sa_url.get_backend_name()
    if backend == "mysql":
        charset = _query_param(sa_url, "charset")
        if charset is None or charset.casefold() != _MYSQL_CHARSET:
            raise DatabaseConfigError(
                "MySQL 连接串必须带 charset=utf8mb4。否则中文和 emoji 可能乱码。"
                "示例: mysql+pymysql://user:password@127.0.0.1:3306/crosserp?charset=utf8mb4"
            )
    engine = create_engine(sa_url)
    if backend == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """提交成功的会话。异常时回滚。未传入引擎时使用 get_database_url()。"""
    owns_engine = engine is None
    bound = make_engine(get_database_url()) if engine is None else engine
    session = Session(bound)
    try:
        with session.begin():
            yield session
    finally:
        session.close()
        if owns_engine:
            bound.dispose()
