"""端点的 x-crosserp 元数据声明。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, ParamSpec, TypeVar, cast

IdempotencyOwner = Literal["dispatcher", "http", "none"]

API_METADATA_KEY = "__crosserp_api_metadata__"
P = ParamSpec("P")
R = TypeVar("R")
ENDPOINT_METADATA: dict[Callable[..., Any], EndpointMetadata] = {}


@dataclass(frozen=True)
class EndpointMetadata:
    entity: str
    action: str
    permission: str
    risk_tier: str
    idempotency: IdempotencyOwner

    def as_openapi(self) -> dict[str, str]:
        return {
            "entity": self.entity,
            "action": self.action,
            "permission": self.permission,
            "riskTier": self.risk_tier,
        }


def api_endpoint(
    *,
    entity: str,
    action: str,
    permission: str,
    risk_tier: str,
    idempotency: IdempotencyOwner,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    metadata = EndpointMetadata(entity, action, permission, risk_tier, idempotency)

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        ENDPOINT_METADATA[function] = metadata
        setattr(function, API_METADATA_KEY, metadata)
        existing = getattr(function, "openapi_extra", {})
        existing = dict(existing) if isinstance(existing, dict) else {}
        existing["x-crosserp"] = metadata.as_openapi()
        cast(Any, function).openapi_extra = existing
        return function

    return decorate


__all__ = ["API_METADATA_KEY", "ENDPOINT_METADATA", "EndpointMetadata", "api_endpoint"]
