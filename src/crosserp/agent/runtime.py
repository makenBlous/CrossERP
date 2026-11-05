"""PydanticAI 问答运行时。真实模型只在用户显式配置后调用。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from crosserp.agent.tools import Citation
from crosserp.agent.verify import verify_numbers

_PROMPT = Path(__file__).parent / "prompts" / "system_v1.md"


class Answer(BaseModel):
    text: str
    citations: list[Citation]
    numbers_checked: bool
    refused: bool
    refusal_reason: str | None
    prompt_version: str
    model: str


def prompt_version() -> str:
    content = _PROMPT.read_bytes()
    return f"{_PROMPT.name}:{hashlib.sha256(content).hexdigest()[:8]}"


def ask(question: str, user_ctx: object | None = None, *, model: Any = None) -> Answer:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("问题不能为空")
    base_url = os.environ.get("CROSSERP_MODEL_BASE_URL", "").strip()
    model_name = os.environ.get("CROSSERP_MODEL", "").strip()
    api_key = os.environ.get("CROSSERP_API_KEY", "").strip()
    if model is None and not all((base_url, model_name, api_key)):
        raise RuntimeError(
            "未配置模型。请设置 CROSSERP_MODEL_BASE_URL、CROSSERP_MODEL、CROSSERP_API_KEY。"
        )
    selected = model_name or getattr(model, "model_name", "offline-test-model")
    if model is None:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
    from pydantic_ai import Agent

    agent = Agent(
        model,
        output_type=str,
        system_prompt=_PROMPT.read_text(encoding="utf-8"),
        retries=0,
        tool_timeout=60,
    )
    result = agent.run_sync(question, deps=user_ctx)
    text = str(result.output).strip()
    checked, reason = verify_numbers(text, [])
    if not text:
        checked, reason = False, "模型返回空回答"
    if not checked:
        return Answer(
            text="无法可靠回答。" if reason else text,
            citations=[],
            numbers_checked=False,
            refused=True,
            refusal_reason=reason,
            prompt_version=prompt_version(),
            model=selected,
        )
    return Answer(
        text=text,
        citations=[],
        numbers_checked=True,
        refused=False,
        refusal_reason=None,
        prompt_version=prompt_version(),
        model=selected,
    )
