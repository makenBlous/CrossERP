"""同步令牌 CSRF 校验。"""

from __future__ import annotations

import hashlib


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def valid_pair(cookie: str | None, submitted: str | None) -> bool:
    return bool(cookie and submitted and token_hash(cookie) == token_hash(submitted))
