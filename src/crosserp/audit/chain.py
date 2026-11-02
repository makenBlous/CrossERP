"""审计哈希。纯函数。不碰数据库。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

GENESIS_PREV_HASH = "0" * 64


def canonical_json(obj: object) -> bytes:
    """规范化 JSON。键排序。中文不转义。无多余空格。"""
    return json.dumps(
        _normalize(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_hash(prev_hash: str, record: object) -> str:
    """sha256(prev_hash 的 UTF-8 + 规范化 JSON) 的十六进制。"""
    if not isinstance(prev_hash, str):
        raise TypeError("prev_hash 必须是字符串")
    body = prev_hash.encode("utf-8") + canonical_json(record)
    return hashlib.sha256(body).hexdigest()


def json_ready(obj: object) -> object:
    """转成可入库的 JSON 值。Decimal 和 datetime 变成字符串。"""
    return _normalize(obj)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("时间必须带时区")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _normalize(obj: object) -> object:
    if obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        raise TypeError("禁止 float。审计规范化不接受浮点数")
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if isinstance(obj, datetime):
        return _iso_utc(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Mapping):
        return {str(key): _normalize(value) for key, value in obj.items()}
    if isinstance(obj, Sequence) and not isinstance(obj, bytes | bytearray):
        return [_normalize(item) for item in obj]
    raise TypeError(f"审计记录无法规范化: {type(obj).__name__}")
