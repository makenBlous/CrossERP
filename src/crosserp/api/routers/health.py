"""API 健康检查样例。"""

from __future__ import annotations

from fastapi import APIRouter

from crosserp import __version__
from crosserp.api.metadata import api_endpoint

router = APIRouter()


@router.get("/health", name="api_health")
@api_endpoint(
    entity="Health", action="Health.read", permission="public", risk_tier="none", idempotency="none"
)
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


__all__ = ["router"]
