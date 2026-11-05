"""回答中的数字引用校验。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from crosserp.agent.tools import Citation

_NUMBER = re.compile(r"(?<![\w^])[-+]?[$€¥]?\d[\d,]*(?:\.\d+)?%?")
_YEAR = re.compile(r"^(?:19|20)\d{2}$")


def verify_numbers(text: str, citations: Iterable[Citation]) -> tuple[bool, str | None]:
    """确认回答每个金额/百分比都能在工具引用中找到相同值。"""
    values = [citation.value for citation in citations]
    normalized = {_number_value(value) for value in values}
    for raw in _NUMBER.findall(text):
        stripped = raw.replace(",", "").replace("$", "").replace("€", "").replace("¥", "")
        if _YEAR.fullmatch(stripped) or stripped.startswith("第"):
            continue
        candidate = _number_value(raw)
        if candidate not in normalized:
            return False, f"回答中的数字 {raw} 没有来源"
    return True, None


def _number_value(value: str) -> str:
    raw = value.strip().replace(",", "").replace("$", "").replace("€", "").replace("¥", "")
    if raw.endswith("%"):
        raw = raw[:-1] + "%"
        number = raw[:-1]
        try:
            return f"{Decimal(number).normalize():f}%"
        except InvalidOperation:
            return raw
    try:
        return f"{Decimal(raw).normalize():f}"
    except InvalidOperation:
        return raw
