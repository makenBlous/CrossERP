"""跨块审计协议, 默认写入现有哈希链。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from crosserp.audit.log import append
from crosserp.platform.principal import Principal


class AuditRecorder(Protocol):
    def record(
        self,
        *,
        principal: Principal,
        entity: str,
        action: str,
        diff: Any,
        evidence: Sequence[Any] | None = None,
        approval_id: UUID | None = None,
        request_id: str | None = None,
        reason: str | None = None,
        tool_call_id: str | None = None,
    ) -> Any: ...


class DefaultAuditRecorder:
    """把新身份上下文映射到旧 audit_log, 保持同一事务与哈希链。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        principal: Principal,
        entity: str,
        action: str,
        diff: Any,
        evidence: Sequence[Any] | None = None,
        approval_id: UUID | None = None,
        request_id: str | None = None,
        reason: str | None = None,
        tool_call_id: str | None = None,
    ) -> Any:
        actor_type = "agent" if principal.is_agent else "user"
        context = {
            "diff": diff,
            "evidence": list(evidence or []),
            "agent_id": principal.agent_id,
            "on_behalf_of": str(principal.on_behalf_of) if principal.on_behalf_of else None,
            "delegation_id": principal.delegation_id,
            "run_id": principal.run_id,
            "is_subagent": principal.is_subagent,
            "channel": principal.channel,
            "tool_call_id": tool_call_id,
        }
        target_id = str(principal.effective_user_id or "request")
        return append(
            self.session,
            actor_type,
            action,
            entity,
            target_id,
            None,
            context,
            actor_user_id=principal.user_id,
            actor_role=next(iter(principal.roles), None),
            approval_id=approval_id,
            request_id=request_id,
            reason=reason,
        )


__all__ = ["AuditRecorder", "DefaultAuditRecorder"]
