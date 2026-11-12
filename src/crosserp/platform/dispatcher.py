"""统一实体动作执行器：所有入口共用同一套检查和事务边界。"""

# 统一错误消息和审计说明沿用项目中文口径。
# ruff: noqa: RUF001, RUF002

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import ActionExecution, DedupCandidate, EntityEvent, EntityVersion
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.audit import AuditRecorder, DefaultAuditRecorder
from crosserp.platform.permissions import PermissionService
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
    """按固定顺序执行动作，并将版本、审计和事件写进同一事务。"""

    STAGES = (
        "identity_and_scope",
        "permission",
        "risk_and_ai_cap",
        "separation_of_duties",
        "idempotency_and_version",
        "business_action",
        "entity_version_and_audit",
    )

    def __init__(
        self,
        hooks: dict[str, Callable[..., Any]] | None = None,
        *,
        session: Session | None = None,
        permission_service: PermissionService | None = None,
        audit_recorder: AuditRecorder | None = None,
        approval_gateway: ApprovalGateway | None = None,
        ai_enabled: bool = True,
        ai_mode: str = "normal",
    ) -> None:
        self.hooks = {} if hooks is None else hooks
        self.session = session
        if permission_service is None:
            raise RuntimeError("ActionDispatcher 必须绑定 PermissionService")
        self.permission_service = permission_service
        self.audit_recorder = audit_recorder
        self.approval_gateway = approval_gateway
        if ai_mode not in {"normal", "degraded", "off"}:
            raise ValueError("ai_mode 必须是 normal、degraded 或 off")
        self.ai_enabled = ai_enabled and ai_mode == "normal"
        self.ai_mode = ai_mode

    def dispatch(
        self,
        *,
        principal: Principal,
        permission: str,
        risk_tier: RiskTier | str,
        action: str,
        business_action: Callable[[], Any],
        hooks: dict[str, Callable[..., Any]] | None = None,
        entity: str | None = None,
        entity_id: UUID | str | None = None,
        payload: Any = None,
        expected_version: int | None = None,
        idempotency_key: str | None = None,
        source_batch_id: UUID | None = None,
        source_raw_row_id: int | None = None,
        source_file: str | None = None,
        request_id: str | None = None,
        tool_call_id: str | None = None,
        parent_permissions: frozenset[str] | None = None,
        represented_permissions: frozenset[str] | None = None,
    ) -> Any:
        all_hooks = dict(self.hooks)
        if hooks is not None:
            all_hooks.update(hooks)
        context: dict[str, Any] = {
            "principal": principal,
            "permission": permission,
            "action": action,
            "entity": action.split(".", 1)[0] if entity is None else entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "payload": payload,
            "expected_version": expected_version,
        }
        with self._transaction():
            self._hook(all_hooks, "identity_and_scope", context)
            self._identity_and_scope(
                principal, permission, parent_permissions, represented_permissions
            )
            context["data_scope"] = self.permission_service.data_scope_filter(
                principal, context["entity"]
            )
            self._hook(all_hooks, "permission", context)
            self.permission_service.require(principal, permission, entity_id)

            decision = can_ai_execute(risk_tier)
            context["autonomy_decision"] = decision
            self._hook(all_hooks, "risk_and_ai_cap", context)
            if (
                principal.is_agent
                and not self.ai_enabled
                and RiskTier(risk_tier) is not RiskTier.NONE
            ):
                raise APIError(ErrorCode.AI_MODE_OFF, "AI 已关闭，动作只能按只读路径执行")
            if principal.is_agent and decision is AutonomyDecision.REJECT:
                raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "智能体不能执行高危动作")

            self._hook(all_hooks, "separation_of_duties", context)
            self._hook(all_hooks, "idempotency_and_version", context)
            replay = self._find_replay(idempotency_key, payload)
            if replay is not None:
                return replay
            current_version = self._current_version(context["entity"], context["entity_id"])
            if expected_version is not None and expected_version != current_version:
                raise APIError(
                    ErrorCode.CONFLICT_VERSION,
                    "实体版本已变化",
                    details={"expectedVersion": expected_version, "actualVersion": current_version},
                )

            if principal.is_agent and decision is AutonomyDecision.DRAFT_OR_APPROVAL:
                if self.approval_gateway is None:
                    raise APIError(ErrorCode.APPROVAL_REQUIRED, "高风险动作需要审批网关")
                approval = self.approval_gateway.submit(
                    principal=principal,
                    entity=context["entity"],
                    action=action,
                    payload=payload,
                    risk_tier=RiskTier(risk_tier).value,
                    approval_type=context["entity"].lower(),
                    request_id=request_id,
                )
                result = _approval_result(approval)
                self._save_execution(
                    principal=principal,
                    action=action,
                    entity=context["entity"],
                    entity_id=context["entity_id"],
                    status="awaiting_approval",
                    result=result,
                    idempotency_key=idempotency_key,
                    request_payload=payload,
                )
                return result

            result = _call_business_action(business_action)
            context["result"] = result
            context["version"] = self._write_version_and_audit(
                principal=principal,
                action=action,
                entity=context["entity"],
                entity_id=context["entity_id"],
                result=result,
                current_version=current_version,
                source_batch_id=source_batch_id,
                source_raw_row_id=source_raw_row_id,
                source_file=source_file,
                request_id=request_id,
                tool_call_id=tool_call_id,
                payload=payload,
            )
            self._emit_events(context, action, result, risk_tier)
            self._save_execution(
                principal=principal,
                action=action,
                entity=context["entity"],
                entity_id=context["entity_id"],
                status="succeeded",
                result={**_as_mapping(result), "version": context.get("version")},
                idempotency_key=idempotency_key,
                request_payload=payload,
            )
            self._hook(all_hooks, "entity_version_and_audit", context)
            return (
                result
                if context.get("version") is None
                else _with_version(result, context["version"])
            )

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.session is None:
            return nullcontext()
        if self.session.in_transaction():
            return self.session.begin_nested()
        return self.session.begin()

    def _identity_and_scope(
        self,
        principal: Principal,
        permission: str,
        parent_permissions: frozenset[str] | None,
        represented_permissions: frozenset[str] | None,
    ) -> None:
        if principal.user_id is None and permission not in {"public", "authenticated"}:
            raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
        current = self.permission_service.current_permissions
        effective = principal.represented_permissions
        if effective is None and principal.is_agent and principal.on_behalf_of is not None:
            effective = frozenset(current(principal))
        represented = effective if represented_permissions is None else represented_permissions
        if represented is not None and not principal.permissions.issubset(represented):
            raise APIError(ErrorCode.DELEGATION_SCOPE_EXCEEDED, "智能体不能扩展被代表人权限")
        if (
            parent_permissions is not None
            and represented is not None
            and not parent_permissions.issubset(represented)
        ):
            raise APIError(ErrorCode.DELEGATION_SCOPE_EXCEEDED, "主智能体不能扩展被代表人权限")
        if (
            principal.is_subagent
            and parent_permissions is not None
            and not principal.permissions.issubset(parent_permissions)
        ):
            raise APIError(ErrorCode.DELEGATION_SCOPE_EXCEEDED, "子智能体不能扩展主智能体权限")
        if (
            represented is not None
            and principal.is_agent
            and principal.on_behalf_of is not None
            and permission not in {"public", "authenticated"}
            and permission not in represented
        ):
            raise APIError(ErrorCode.PERMISSIONS_CHANGED, "被代表人的权限已变化")

    def _hook(
        self, hooks: dict[str, Callable[..., Any]], name: str, context: dict[str, Any]
    ) -> None:
        hook = hooks.get(name)
        if hook is not None:
            hook(**context)

    def _current_version(self, entity: str, entity_id: str | None) -> int:
        if self.session is None or entity_id is None:
            return 0
        value = self.session.scalar(
            select(func.max(EntityVersion.version)).where(
                EntityVersion.entity_type == entity, EntityVersion.entity_id == entity_id
            )
        )
        if value is not None:
            return int(value)
        if entity == "DedupCandidate":
            candidate = self.session.get(DedupCandidate, UUID(entity_id))
            if candidate is not None:
                return candidate.version
        return 0

    def _find_replay(self, key: str | None, payload: Any) -> Any:
        if self.session is None or not key:
            return None
        row = self.session.scalar(
            select(ActionExecution).where(ActionExecution.idempotency_key == key)
        )
        if row is None:
            return None
        if row.request_hash != _request_hash(payload):
            raise APIError(ErrorCode.IDEMPOTENCY_REPLAY_MISMATCH, "幂等键对应了不同请求体")
        return row.result_json

    def _write_version_and_audit(
        self,
        *,
        principal: Principal,
        action: str,
        entity: str,
        entity_id: str | None,
        result: Any,
        current_version: int,
        source_batch_id: UUID | None,
        source_raw_row_id: int | None,
        source_file: str | None,
        request_id: str | None,
        tool_call_id: str | None,
        payload: Any,
    ) -> int | None:
        if self.session is None or entity_id is None:
            return None
        values = _as_mapping(result)
        before = values.get("before")
        if before is None and isinstance(payload, dict):
            before = payload.get("before")
        after = values.get("after", result)
        diff = values.get("diff", {"before": before, "after": after})
        recorder = self.audit_recorder or DefaultAuditRecorder(self.session)
        audit = recorder.record(
            principal=principal,
            entity=entity,
            action=action,
            diff=diff,
            request_id=request_id,
            tool_call_id=tool_call_id,
        )
        row = EntityVersion(
            id=uuid4(),
            entity_type=entity,
            entity_id=entity_id,
            version=current_version + 1,
            changed_at=datetime.now(UTC),
            actor_type="agent" if principal.is_agent else "human",
            actor_id=principal.user_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
            action_id=action,
            source_batch_id=source_batch_id,
            source_raw_row_id=source_raw_row_id,
            source_file=source_file,
            before_json=before,
            after_json=after,
            diff_json=diff,
            audit_log_id=audit.id,
        )
        self.session.add(row)
        self.session.flush()
        return row.version

    def _emit_events(
        self, context: dict[str, Any], action: str, result: Any, risk_tier: RiskTier | str
    ) -> None:
        if self.session is None or context.get("entity_id") is None:
            return
        self.session.add(
            EntityEvent(
                id=uuid4(),
                event_type=f"{context['entity'].lower()}.{action.rsplit('.', 1)[-1]}.done",
                entity_type=context["entity"],
                entity_id=context["entity_id"],
                action_id=action,
                payload_json={"result": _jsonable(result), "riskTier": RiskTier(risk_tier).value},
                created_at=datetime.now(UTC),
            )
        )
        if RiskTier(risk_tier) is RiskTier.MEDIUM:
            reversible_until = datetime.now(UTC) + timedelta(hours=24)
            self.session.add(
                EntityEvent(
                    id=uuid4(),
                    event_type="notification.daily_summary",
                    entity_type=context["entity"],
                    entity_id=context["entity_id"],
                    action_id=action,
                    payload_json={
                        "action": action,
                        "notificationKind": "daily_summary",
                        "reversibleUntil": reversible_until.isoformat(),
                    },
                    created_at=datetime.now(UTC),
                )
            )

    def _save_execution(
        self,
        *,
        principal: Principal,
        action: str,
        entity: str,
        entity_id: str | None,
        status: str,
        result: Any,
        idempotency_key: str | None,
        request_payload: Any,
    ) -> None:
        if self.session is None:
            return
        self.session.add(
            ActionExecution(
                id=uuid4(),
                idempotency_key=idempotency_key,
                request_hash=_request_hash(request_payload),
                entity_type=entity,
                entity_id=entity_id,
                action_id=action,
                actor_type="agent" if principal.is_agent else "human",
                status=status,
                result_json=_jsonable(result),
                version=result.get("version") if isinstance(result, dict) else None,
                created_at=datetime.now(UTC),
            )
        )


def _call_business_action(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except TypeError as exc:
        raise APIError(ErrorCode.INTERNAL_ERROR, "业务动作必须是无参可调用对象") from exc


def _approval_result(value: dict[str, Any]) -> dict[str, Any]:
    return value


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {"value": value}


def _with_version(value: Any, version: int) -> Any:
    return (
        {**value, "version": version}
        if isinstance(value, dict)
        else {"result": value, "version": version}
    )


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _request_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


__all__ = ["ActionDispatcher", "AutonomyDecision", "RiskTier", "can_ai_execute"]
