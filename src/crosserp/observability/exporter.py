"""把一次 AI 调用落库; 失败时由调用方记录 warning, 不阻断回答。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import LlmCall, PromptVersion
from crosserp.observability.prices import estimate_cost


def record_call(
    session: Session,
    *,
    model: str,
    question: str,
    answer: str,
    prompt_name: str,
    prompt_content: str,
    status: str,
    refusal_reason: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    username: str | None = None,
) -> LlmCall:
    digest = hashlib.sha256(prompt_content.encode("utf-8")).hexdigest()
    prompt = session.scalar(
        select(PromptVersion).where(
            PromptVersion.name == prompt_name, PromptVersion.sha256 == digest
        )
    )
    if prompt is None:
        prompt = PromptVersion(
            id=uuid4(),
            name=prompt_name,
            version=prompt_name,
            sha256=digest,
            content=prompt_content,
            created_at=datetime.now(UTC),
        )
        session.add(prompt)
        session.flush()
    row = LlmCall(
        id=uuid4(),
        ts=datetime.now(UTC),
        user_id=None,
        username=username,
        channel="cli",
        model=model,
        prompt_version_id=prompt.id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_estimate=estimate_cost(model, input_tokens, output_tokens),
        currency="USD",
        status=status,
        refusal_reason=refusal_reason,
        question_text=question,
        answer_text=answer,
        trace_id=uuid4().hex,
        request_id=None,
    )
    session.add(row)
    session.flush()
    return row
