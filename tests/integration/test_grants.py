"""数据库账号权限验收。CI/本地授权账号未配置时跳过。"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from crosserp.db.session import make_engine

pytestmark = pytest.mark.db


def _grant_url(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"未设置 {name}，跳过账号权限验收")  # noqa: RUF001
    return value


def test_app_cannot_update_or_delete_audit_log() -> None:
    engine = make_engine(_grant_url("CROSSERP_GRANTS_APP_URL"))
    try:
        with engine.begin() as connection, pytest.raises(SQLAlchemyError):
            connection.execute(text("UPDATE audit_log SET reason = 'blocked'"))
        with engine.begin() as connection, pytest.raises(SQLAlchemyError):
            connection.execute(text("DELETE FROM audit_log"))
    finally:
        engine.dispose()


def test_agent_cannot_insert_business_row() -> None:
    engine = make_engine(_grant_url("CROSSERP_GRANTS_AGENT_URL"))
    try:
        with engine.begin() as connection, pytest.raises(SQLAlchemyError):
            connection.execute(
                text(
                    "INSERT INTO store (id, platform, marketplace, name, currency) "
                    "VALUES ('00000000-0000-0000-0000-000000000002', 'x', 'x', 'x', 'USD')"
                )
            )
    finally:
        engine.dispose()
