"""仓库规则 Markdown 的可解释关键词检索。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN = re.compile(r"[\w]+", re.UNICODE)


@dataclass(frozen=True)
class RuleHit:
    text: str
    file: str
    line_start: int
    line_end: int
    score: int


def search_rules_doc(query: str, k: int = 5, *, root: Path | None = None) -> list[RuleHit]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("检索词不能为空")
    if k < 1 or k > 20:
        raise ValueError("k 必须在 1 到 20 之间")
    rules_root = root or Path(__file__).resolve().parents[3] / "docs" / "rules"
    terms = [item.casefold() for item in _TOKEN.findall(query)]
    hits: list[RuleHit] = []
    for path in sorted(rules_root.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            lowered = line.casefold()
            score = sum(lowered.count(term) for term in terms)
            if score:
                hits.append(
                    RuleHit(line.strip(), str(path.relative_to(rules_root)), number, number, score)
                )
    hits.sort(key=lambda item: (-item.score, item.file, item.line_start))
    return hits[:k]
