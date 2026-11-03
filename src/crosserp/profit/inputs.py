"""Stable input identity hashing for profit snapshots."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

CALC_VERSION = "0.1.0"


def inputs_hash(record_ids: Iterable[object], calc_version: str = CALC_VERSION) -> str:
    """Hash sorted input ids and calculation version exactly once."""
    values = sorted(str(value) for value in record_ids)
    payload = "\n".join(values) + "\n" + calc_version
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
