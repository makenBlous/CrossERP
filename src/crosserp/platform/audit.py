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
        evidence: Sequence[Any] = (),
        approval_id: UUID | None = None,
        request_id: str | None = None,
        reason: str | None = None,
        tool_call_id: str | None = None,
        subagent_name: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        llm_call: str | None = None,
        confidence: Any = None,
        autonomy_level: str | None = None,
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
        evidence: Sequence[Any] = (),
        approval_id: UUID | None = None,
        request_id: str | None = None,
        reason: str | None = None,
        tool_call_id: str | None = None,
        subagent_name: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        llm_call: str | None = None,
        confidence: Any = None,
        autonomy_level: str | None = None,
    ) -> Any:
        actor_type = "agent" if principal.is_agent else "human"
        safe_diff = _redact_sensitive(diff)
        context = {
            "diff": safe_diff,
            "evidence": list(evidence),
            "agent_id": principal.agent_id,
            "on_behalf_of": str(principal.on_behalf_of) if principal.on_behalf_of else None,
            "delegation_id": principal.delegation_id,
            "run_id": principal.run_id,
            "is_subagent": principal.is_subagent,
            "channel": principal.channel,
            "tool_call_id": tool_call_id,
            "subagent_name": subagent_name,
            "model": model,
            "prompt_version": prompt_version,
            "llm_call": llm_call,
            "confidence": confidence,
            "autonomy_level": autonomy_level,
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
            agent_id=principal.agent_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
            entity_type=entity,
            entity_id=target_id,
            diff_json=safe_diff,
            evidence_json=list(evidence),
            subagent_name=subagent_name,
            model=model,
            prompt_version=prompt_version,
            llm_call=llm_call,
            confidence=confidence,
            autonomy_level=autonomy_level,
        )


__all__ = ["AuditRecorder", "DefaultAuditRecorder"]


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "已修改"
            if any(
                token in str(key).casefold()
                for token in ("password", "secret", "token", "api_key", "apikey")
            )
            else _redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value
