"""智能体只读数据库会话入口。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from crosserp.db.session import readonly_session


@contextmanager
def agent_session() -> Iterator[Session]:
    """只提供 SELECT 权限的会话; 不回退到应用写账号。"""
    with readonly_session() as session:
        yield session
