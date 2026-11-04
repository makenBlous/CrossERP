"""MySQL/PG 只读事务双保险。"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from crosserp.db.session import readonly_session

pytestmark = pytest.mark.db


def test_configured_agent_session_rejects_insert() -> None:
    if not os.environ.get("CROSSERP_AGENT_DATABASE_URL"):
        pytest.skip("未设置 CROSSERP_AGENT_DATABASE_URL，跳过外部智能体账号测试")  # noqa: RUF001
    with readonly_session() as session, pytest.raises(SQLAlchemyError):
        session.execute(
            text(
                "INSERT INTO store (id, platform, marketplace, name, currency) "
                "VALUES ('00000000-0000-0000-0000-000000000003', 'x', 'x', 'x', 'USD')"
            )
        )
