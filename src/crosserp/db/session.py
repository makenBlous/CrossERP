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
from crosserp.db.dialects import set_readonly_transaction

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


def get_migrate_database_url() -> str:
    """迁移账号连接串；未配置时沿用应用连接串。"""  # noqa: RUF002
    _load_env_file()
    return os.environ.get("CROSSERP_MIGRATE_DATABASE_URL", "").strip() or get_database_url()


def get_agent_database_url() -> str:
    """智能体只读账号连接串；本地未单独配置时沿用应用连接串。"""  # noqa: RUF002
    _load_env_file()
    return os.environ.get("CROSSERP_AGENT_DATABASE_URL", "").strip() or get_database_url()


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


def make_readonly_engine(url: str) -> Engine:
    """创建只读引擎。SQLite 使用 mode=ro URI，三库均设置只读事务。"""  # noqa: RUF002
    sa_url = make_url(url)
    if sa_url.get_backend_name() == "sqlite":
        if not sa_url.database or sa_url.database == ":memory:":
            raise DatabaseConfigError("SQLite 只读会话必须连接已有文件，不能使用内存库")  # noqa: RUF001
        readonly = URL.create(
            drivername="sqlite",
            database=f"file:{Path(sa_url.database).expanduser().resolve()}?mode=ro",
        )
        return create_engine(readonly, connect_args={"uri": True})
    engine = make_engine(url)
    return engine


@contextmanager
def readonly_session() -> Iterator[Session]:
    """打开智能体专用只读会话。"""
    url = get_agent_database_url()
    engine = make_readonly_engine(url)
    session = Session(engine)
    try:
        if engine.dialect.name != "sqlite":
            set_readonly_transaction(session)
        yield session
    finally:
        session.close()
        engine.dispose()


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """提交成功的会话。异常时回滚。未传入引擎时使用 get_database_url()。"""
    owns_engine = engine is None
    bound = make_engine(get_database_url()) if engine is None else engine
    # 页面和 CLI 会在事务关闭后渲染查询结果; 保留已读取字段, 避免把
    # 已提交的 ORM 对象交给模板时触发 detached refresh。
    session = Session(bound, expire_on_commit=False)
    try:
        with session.begin():
            yield session
    finally:
        session.close()
        if owns_engine:
            bound.dispose()
