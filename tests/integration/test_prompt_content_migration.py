"""T52 提示词正文类型迁移保留数据和正文哈希。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import select

from crosserp.db.migrate import downgrade_base, make_alembic_config, upgrade_head
from crosserp.db.schema import PromptVersion
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db


def test_prompt_content_migration_preserves_value_and_hash(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    content = "规则正文: " + "跨境对账。" * 100
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    row_id = uuid4()
    try:
        with session_scope(engine) as session:
            session.add(
                PromptVersion(
                    id=row_id,
                    name="migration-test",
                    version="migration-test",
                    sha256=digest,
                    content=content,
                    created_at=datetime.now(UTC),
                )
            )
        command.downgrade(make_alembic_config(url), "0017_eval_run")
        command.upgrade(make_alembic_config(url), "head")
        with session_scope(engine) as session:
            row = session.scalar(select(PromptVersion).where(PromptVersion.id == row_id))
            assert row is not None
            assert row.content == content
            assert row.sha256 == digest
            assert hashlib.sha256(row.content.encode("utf-8")).hexdigest() == row.sha256
    finally:
        downgrade_base(url)
