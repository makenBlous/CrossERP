"""审计哈希。hash = sha256(prev_hash + 规范化 JSON)。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

GENESIS_HASH = "0" * 64


def canonical_json(obj: object) -> bytes:
    """稳定 JSON。键排序。Decimal 转字符串。时间转 UTC ISO-8601。"""
    text = json.dumps(
        to_jsonable(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def compute_hash(prev_hash: str, record: object) -> str:
    """sha256(prev_hash 的 UTF-8 + canonical_json) 的十六进制。"""
    payload = prev_hash.encode("utf-8") + canonical_json(record)
    return hashlib.sha256(payload).hexdigest()


def to_jsonable(value: object) -> object:
    """收成 json.dumps 能直接写的结构。禁止 float。"""
    if value is None or isinstance(value, str | bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise TypeError("审计记录禁止 float")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return _utc_text(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    raise TypeError(f"无法写入审计的类型 {type(value).__name__}")


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("审计时间必须带时区")
    return value.astimezone(UTC).isoformat()
