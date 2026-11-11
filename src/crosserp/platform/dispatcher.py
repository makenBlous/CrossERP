"""统一动作执行器的接口、阶段顺序和 AI 风险上限。"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from crosserp.api.errors import APIError, ErrorCode
from crosserp.platform.principal import Principal


class RiskTier(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomyDecision(StrEnum):
    EXECUTE = "execute"
    DRAFT_OR_APPROVAL = "draft_or_approval"
    REJECT = "reject"


def can_ai_execute(risk_tier: RiskTier | str) -> AutonomyDecision:
    tier = RiskTier(risk_tier)
    if tier in {RiskTier.NONE, RiskTier.LOW, RiskTier.MEDIUM}:
        return AutonomyDecision.EXECUTE
    if tier is RiskTier.HIGH:
        return AutonomyDecision.DRAFT_OR_APPROVAL
    return AutonomyDecision.REJECT


class ActionDispatcher:
    """可注入各领域业务动作的最小执行器骨架。"""

    STAGES = (
        "identity_and_scope",
        "permission",
        "risk_and_ai_cap",
        "separation_of_duties",
        "idempotency_and_version",
        "business_action",
        "entity_version_and_audit",
    )

    def __init__(self, hooks: dict[str, Callable[..., Any]] | None = None) -> None:
        self.hooks = hooks or {}

    def dispatch(
        self,
        *,
        principal: Principal,
        permission: str,
        risk_tier: RiskTier | str,
        action: str,
        business_action: Callable[[], Any],
        hooks: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        all_hooks = dict(self.hooks)
        all_hooks.update(hooks or {})
        context = {"principal": principal, "permission": permission, "action": action}
        _run_hook(all_hooks, "identity_and_scope", context)
        _run_hook(all_hooks, "permission", context)
        decision = can_ai_execute(risk_tier)
        if principal.is_agent and decision is AutonomyDecision.REJECT:
            raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "智能体不能执行危风险动作")
        context["autonomy_decision"] = decision
        _run_hook(all_hooks, "risk_and_ai_cap", context)
        _run_hook(all_hooks, "separation_of_duties", context)
        _run_hook(all_hooks, "idempotency_and_version", context)
        result = business_action()
        context["result"] = result
        _run_hook(all_hooks, "entity_version_and_audit", context)
        return result


def _run_hook(hooks: dict[str, Callable[..., Any]], name: str, context: dict[str, Any]) -> None:
    hook = hooks.get(name)
    if hook is not None:
        hook(**context)


__all__ = ["ActionDispatcher", "AutonomyDecision", "RiskTier", "can_ai_execute"]
