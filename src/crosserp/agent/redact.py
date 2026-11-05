"""模型上下文的个人信息脱敏和数据边界包裹。"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any

_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)")
_ID = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_SENSITIVE_KEYS = {"buyer_name", "ship_address", "shipping_address", "buyer_phone", "buyer_email"}


class Redactor:
    def __init__(self) -> None:
        self._numbers: dict[tuple[str, str], int] = {}

    def redact(self, value: Any) -> Any:
        if isinstance(value, MutableMapping):
            return {str(key): self._redact_field(str(key), item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value

    def _redact_field(self, key: str, value: Any) -> Any:
        if key.casefold() in _SENSITIVE_KEYS and isinstance(value, str):
            return self._placeholder("field", value)
        return self.redact(value)

    def _redact_text(self, value: str) -> str:
        value = _EMAIL.sub(lambda match: self._placeholder("邮箱", match.group()), value)
        value = _PHONE.sub(lambda match: self._placeholder("手机号", match.group()), value)
        return _ID.sub(lambda match: self._placeholder("身份证号", match.group()), value)

    def _placeholder(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self._numbers:
            self._numbers[key] = len([item for item in self._numbers if item[0] == kind]) + 1
        return f"«已隐藏:{kind}#{self._numbers[key]}»"


def redact(value: Any) -> Any:
    return Redactor().redact(value)


def wrap_data(source: str, value: str) -> str:
    escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<data source="{source}">{escaped}</data>'
