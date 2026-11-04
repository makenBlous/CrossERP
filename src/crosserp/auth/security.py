"""安全事件接口占位; T34 接入独立 security_event 哈希链。"""

from __future__ import annotations

from typing import Any


def record_security_event(*_args: Any, **_kwargs: Any) -> None:
    """暂不落库。保留统一调用接口给 T33/T34。"""
    return None
