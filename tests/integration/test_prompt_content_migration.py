"""T52 提示词正文类型迁移保留数据和正文哈希。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import delete, select

from crosserp.db.migrate import downgrade_base, make_alembic_config, upgrade_head
from crosserp.db.schema import LlmCall, PromptVersion
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


def test_llm_text_migration_preserves_data_and_prompt_hash(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    prompt = "系统规则: " + "跨境对账。" * 100
    question = "问题: " + "订单详情。" * 100
    answer = "回答: " + "引用原始行。" * 100
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    prompt_id = uuid4()
    call_id = uuid4()
    try:
        with session_scope(engine) as session:
            session.add(
                PromptVersion(
                    id=prompt_id,
                    name="llm-migration-test",
                    version="llm-migration-test",
                    sha256=digest,
                    content=prompt,
                    created_at=datetime.now(UTC),
                )
            )
            session.flush()
            session.add(
                LlmCall(
                    id=call_id,
                    ts=datetime.now(UTC),
                    user_id=None,
                    username=None,
                    channel="cli",
                    model="test",
                    prompt_version_id=prompt_id,
                    input_tokens=1,
                    output_tokens=1,
                    latency_ms=1,
                    cost_estimate=None,
                    currency="USD",
                    status="ok",
                    refusal_reason=None,
                    question_text=question,
                    answer_text=answer,
                    trace_id="a" * 32,
                    request_id=None,
                )
            )
        command.downgrade(make_alembic_config(url), "0018_prompt_content_text")
        command.upgrade(make_alembic_config(url), "head")
        with session_scope(engine) as session:
            prompt_row = session.scalar(select(PromptVersion).where(PromptVersion.id == prompt_id))
            call_row = session.scalar(select(LlmCall).where(LlmCall.id == call_id))
            assert prompt_row is not None and prompt_row.content == prompt
            assert prompt_row.sha256 == digest
            assert call_row is not None
            assert call_row.question_text == question
            assert call_row.answer_text == answer
            assert hashlib.sha256(prompt_row.content.encode("utf-8")).hexdigest() == digest
    finally:
        with session_scope(engine) as session:
            session.execute(delete(LlmCall).where(LlmCall.id == call_id))
            session.execute(delete(PromptVersion).where(PromptVersion.id == prompt_id))
        downgrade_base(url)
