from pathlib import Path

import pytest
from sqlalchemy import select

from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import LlmCall
from crosserp.db.session import session_scope
from crosserp.observability.exporter import record_call

pytestmark = pytest.mark.db


def test_llm_call_tables_store_prompt_and_call(engine, tmp_path: Path) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = record_call(
                session,
                model="m",
                question="测试",
                answer="回答",
                prompt_name="system_v1.md",
                prompt_content="规则",
                status="ok",
                input_tokens=1,
                output_tokens=2,
            )
            assert session.scalar(select(LlmCall).where(LlmCall.id == row.id)) is not None
    finally:
        downgrade_base(url)
