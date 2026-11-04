"""智能体会话在 SQLite 中拒绝写入。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.session import readonly_session, sqlite_file_url

pytestmark = pytest.mark.guard


def test_sqlite_readonly_session_rejects_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "readonly.db"
    url = sqlite_file_url(database)
    upgrade_head(url)
    try:
        monkeypatch.setenv("CROSSERP_AGENT_DATABASE_URL", url)
        with readonly_session() as session, pytest.raises(SQLAlchemyError):
            session.execute(
                text(
                    "INSERT INTO store (id, platform, marketplace, name, currency) "
                    "VALUES ('00000000-0000-0000-0000-000000000001', 'x', 'x', 'x', 'USD')"
                )
            )
    finally:
        downgrade_base(url)
