"""幂等键持久化模型和公共查询工具。"""

from __future__ import annotations

from collections.abc import Callable

from crosserp.db.schema import IdempotencyKey

IDEMPOTENCY_OWNER_KEY = "__crosserp_idempotency_owner__"


def dispatcher_idempotency[F: Callable[..., object]](endpoint: F) -> F:
    """声明该写动作的幂等由 ActionDispatcher 在权限校验之后处理。"""
    setattr(endpoint, IDEMPOTENCY_OWNER_KEY, "dispatcher")
    return endpoint


__all__ = ["IDEMPOTENCY_OWNER_KEY", "IdempotencyKey", "dispatcher_idempotency"]
