"""运行 20 道离线评测题。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[3]
QUESTIONS = ROOT / "tests" / "eval" / "questions.yaml"


def load_questions() -> list[dict[str, Any]]:
    raw = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("评测题文件必须是列表")
    return [item for item in raw if isinstance(item, dict)]


def run(model: str = "test", output: Path | None = None) -> dict[str, Any]:
    if model != "test":
        raise RuntimeError("真实模型评测由 maken 手工执行; 离线模式只支持 --model test")
    from crosserp.evals.scorers import score

    results = []
    for question in load_questions():
        if question.get("must_refuse"):
            answer = "数据不足, 无法可靠回答。"
        else:
            answer = ";".join(str(item) for item in question.get("expected_facts", []))
        citations = [{"value": str(item)} for item in question.get("must_cite", [])]
        results.append(score(question, answer, citations))
    result = {
        "model": model,
        "total": len(results),
        "passed": sum(item["passed"] for item in results),
        "results": results,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
