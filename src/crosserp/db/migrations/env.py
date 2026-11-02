"""Alembic 环境。连接串只读 CROSSERP_DATABASE_URL。或调用方传入的 connection_url。

render_as_batch 打开。方便以后在 SQLite 上做 ALTER。非 SQLite 仍发普通 DDL。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

_SRC = Path(__file__).resolve().parents[3]
if _SRC.name == "src" and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from alembic import context  # noqa: E402
from alembic.autogenerate.api import AutogenContext  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402

from crosserp.db.schema import Base  # noqa: E402
from crosserp.db.session import get_database_url, make_engine  # noqa: E402
from crosserp.db.types import FxRate, Money4, UtcDateTime  # noqa: E402

config = context.config
target_metadata = Base.metadata


def _resolve_url() -> str:
    override = config.attributes.get("connection_url")
    if isinstance(override, str) and override.strip():
        return override.strip()
    return get_database_url()


def _render_item(
    type_: str, obj: Any, autogen_context: AutogenContext
) -> str | Literal[False]:
    """自定义类型按类名渲染。避免生成方言专属类型。"""
    if type_ == "type" and isinstance(obj, Money4 | FxRate | UtcDateTime):
        autogen_context.imports.add("from crosserp.db.types import FxRate, Money4, UtcDateTime")
        return f"{type(obj).__name__}()"
    return False


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        compare_server_default=False,
        render_item=_render_item,
    )


def run_migrations_offline() -> None:
    """离线模式只渲染 SQL。不连接数据库。"""
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线迁移。优先复用调用方传入的连接。"""
    given = config.attributes.get("connection")
    if isinstance(given, Connection):
        _configure(given)
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = make_engine(_resolve_url())
    try:
        with engine.connect() as connection:
            _configure(connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
