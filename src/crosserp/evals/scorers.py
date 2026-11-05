"""评测答案评分器, 不调用模型。"""

from __future__ import annotations

from typing import Any


def score(
    question: dict[str, Any], answer: str, citations: list[Any] | None = None
) -> dict[str, Any]:
    expected = [str(item) for item in question.get("expected_facts", [])]
    must_refuse = bool(question.get("must_refuse"))
    refused = "数据不足" in answer or "无法可靠回答" in answer
    facts_ok = all(item in answer for item in expected)
    citation_text = " ".join(str(item) for item in (citations or []))
    required = [str(item) for item in question.get("must_cite", [])]
    citations_ok = all(item in citation_text for item in required)
    passed = refused == must_refuse and facts_ok and citations_ok
    return {
        "id": question["id"],
        "passed": passed,
        "facts_ok": facts_ok,
        "citations_ok": citations_ok,
        "refused": refused,
        "expected_refusal": must_refuse,
    }
