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

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import ActionExecution, AgentUndo, EntityEvent, EntityVersion
from crosserp.iam.scope import AllStores
from crosserp.ontology.catalog import load_catalog
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.audit import AuditRecorder
from crosserp.platform.idempotency import execution_scope, find_action_replay
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal
from crosserp.platform.undo import UndoRestoreRegistry

_CATALOG = load_catalog()


def _event_type(action: str) -> str:
    """事件名只来自实体目录 emits。查询动作不产生事件。"""
    action_def = _CATALOG.action_by_id.get(action)
    if action_def is None or not action_def.emits:
        raise APIError(ErrorCode.VALIDATION_FAILED, "实体目录未声明事件名")
    return action_def.emits[0]


def _has_store_dimension(entity: str) -> bool:
    entity_def = _CATALOG.entity_by_id.get(entity)
    if entity_def is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "该实体不支持撤销")
    return any(item.split(":", 1)[0].strip() == "storeId" for item in entity_def.properties)


class UndoPayload(BaseModel):
    """撤销登记的非空 JSON 对象。"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    entity: str
    entity_id: str = Field(alias="entityId")
    action: str
    permission: str
    before: dict[str, Any]
    actor_id: str | None = Field(alias="actorId")
    on_behalf_of: str | None = Field(alias="onBehalfOf")
    actor_type: str = Field(alias="actorType")
    reverse_action: str | None = Field(alias="reverseAction")
    reverse_payload: dict[str, Any] | None = Field(alias="reversePayload")
    reverse_permission: str | None = Field(alias="reversePermission")


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
        session: Session,
        permission_service: PermissionService,
        audit_recorder: AuditRecorder,
        approval_gateway: ApprovalGateway,
        undo_restore: UndoRestoreRegistry,
        ai_enabled: bool = True,
        ai_mode: str = "normal",
    ) -> None:
        self.hooks = {} if hooks is None else hooks
        self.session = session
        self.permission_service = permission_service
        self.audit_recorder = audit_recorder
        self.approval_gateway = approval_gateway
        self.undo_restore = undo_restore
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
        source_rule_version: str | None = None,
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
            replay = find_action_replay(
                self.session,
                principal,
                key=idempotency_key,
                payload=payload,
                action=action,
            )
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
                approval = self.approval_gateway.submit(
                    principal=principal,
                    entity=context["entity"],
                    action=action,
                    payload=payload,
                    risk_tier=RiskTier(risk_tier).value,
                    approval_type=context["entity"].lower(),
                    request_id=request_id,
                )
                result = approval.to_payload()
                approval_id = approval.approval_id
                self.audit_recorder.record(
                    principal=principal,
                    entity=context["entity"],
                    action=action,
                    diff={"before": None, "after": _jsonable(result)},
                    approval_id=approval_id,
                    request_id=request_id,
                    tool_call_id=tool_call_id,
                )
                self._save_execution(
                    principal=principal,
                    action=action,
                    entity=context["entity"],
                    entity_id=context["entity_id"],
                    status="awaiting_approval",
                    result=result,
                    idempotency_key=idempotency_key,
                    request_payload=payload,
                    approval_id=approval_id,
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
                source_rule_version=source_rule_version,
                request_id=request_id,
                tool_call_id=tool_call_id,
                payload=payload,
            )
            undo = self._create_undo(
                principal=principal,
                action=action,
                permission=permission,
                entity=context["entity"],
                entity_id=context["entity_id"],
                result=result,
                version=context.get("version"),
                risk_tier=risk_tier,
            )
            self._emit_events(context, action, result, risk_tier, undo)
            returned = _with_undo(
                result
                if context.get("version") is None
                else _with_version(result, context["version"]),
                undo,
            )
            self._save_execution(
                principal=principal,
                action=action,
                entity=context["entity"],
                entity_id=context["entity_id"],
                status="succeeded",
                result=returned,
                idempotency_key=idempotency_key,
                request_payload=payload,
                approval_id=None,
            )
            self._hook(all_hooks, "entity_version_and_audit", context)
            return returned

    def undo(
        self,
        undo_id: UUID | str,
        *,
        principal: Principal,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """以同一执行器撤销中风险动作，并重新校验写权限和店铺范围。"""
        if principal.user_id is None:
            raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
        try:
            key = UUID(str(undo_id))
        except ValueError as exc:
            raise APIError(ErrorCode.NOT_FOUND, "撤销记录不存在") from exc
        row = self.session.get(AgentUndo, key)
        if row is None or not self._can_undo(row, principal):
            raise APIError(ErrorCode.NOT_FOUND, "撤销记录不存在")
        payload = UndoPayload.model_validate(row.undo_payload_json)
        if not self.undo_restore.supports(payload.entity):
            raise APIError(ErrorCode.VALIDATION_FAILED, "该实体不支持撤销")
        self._require_undo_target_access(row, principal, payload)
        request_payload = {"undoId": str(row.id)}
        replay = find_action_replay(
            self.session,
            principal,
            key=idempotency_key,
            payload=request_payload,
            action="AgentSuggestion.undo",
        )
        if replay is not None:
            return _as_mapping(replay)
        if row.undone_at is not None:
            raise APIError(ErrorCode.UNDO_ALREADY_APPLIED, "动作已经撤销")
        if datetime.now(UTC) > row.deadline_at:
            raise APIError(ErrorCode.UNDO_EXPIRED, "撤销期限已过")
        current_version = self._current_version(row.entity_type, row.entity_id)
        if current_version != row.action_version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "实体已被后续动作修改，无法撤销",
                details={"expectedVersion": row.action_version, "actualVersion": current_version},
            )
        version_row = self.session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == row.entity_type,
                EntityVersion.entity_id == row.entity_id,
                EntityVersion.version == row.action_version,
            )
        )
        if version_row is None:
            raise APIError(ErrorCode.CONFLICT_VERSION, "撤销版本不存在")

        fields = self.undo_restore.restorable_fields(payload.entity)
        has_restorable = any(name in payload.before for name in fields)
        use_reverse = payload.reverse_action is not None and not has_restorable
        if use_reverse:
            if (
                payload.reverse_action is None
                or payload.reverse_payload is None
                or payload.reverse_permission is None
            ):
                raise APIError(ErrorCode.VALIDATION_FAILED, "撤销反向动作未声明权限")
            self.permission_service.require(principal, payload.reverse_permission, row.entity_id)
            reverse_action = payload.reverse_action
            reverse_payload = payload.reverse_payload

            def restore() -> dict[str, Any]:
                return self.undo_restore.apply_reverse(
                    self.session,
                    action=reverse_action,
                    entity_id=row.entity_id,
                    payload=reverse_payload,
                    principal=principal,
                    permission_service=self.permission_service,
                )
        else:
            if not has_restorable:
                raise APIError(ErrorCode.VALIDATION_FAILED, "撤销前快照没有可回退字段")

            def restore() -> dict[str, Any]:
                self.undo_restore.restore(
                    self.session, row.entity_type, row.entity_id, payload.before
                )
                return {"before": version_row.after_json, "after": payload.before}

        result = self.dispatch(
            principal=principal,
            permission=payload.permission,
            risk_tier=RiskTier.CRITICAL,
            action="AgentSuggestion.undo",
            entity=row.entity_type,
            entity_id=row.entity_id,
            payload=request_payload,
            expected_version=row.action_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            business_action=restore,
        )
        row.undone_by = principal.effective_user_id or principal.user_id
        row.undone_at = datetime.now(UTC)
        self.session.flush()
        return {**_as_mapping(result), "undone": True, "undoId": str(row.id)}

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.session.in_transaction():
            return nullcontext()
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
        current_permissions = self.permission_service.current_permissions(principal)
        effective = principal.represented_permissions
        if effective is None and principal.is_agent and principal.on_behalf_of is not None:
            effective = current_permissions
        represented = effective if represented_permissions is None else represented_permissions
        if represented is not None and not current_permissions.issubset(represented):
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
            and not current_permissions.issubset(parent_permissions)
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
        if entity_id is None:
            return 0
        value = self.session.scalar(
            select(func.max(EntityVersion.version)).where(
                EntityVersion.entity_type == entity, EntityVersion.entity_id == entity_id
            )
        )
        if value is not None:
            return int(value)
        return 0

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
        source_rule_version: str | None,
        request_id: str | None,
        tool_call_id: str | None,
        payload: Any,
    ) -> int | None:
        if entity_id is None:
            return None
        values = _as_mapping(result)
        before = values.get("before")
        if before is None and isinstance(payload, dict):
            before = payload.get("before")
        after = values.get("after", result)
        diff = values.get("diff", {"before": before, "after": after})
        audit = self.audit_recorder.record(
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
            source_rule_version=source_rule_version,
            before_json=before,
            after_json=after,
            diff_json=diff,
            audit_log_id=audit.id,
        )
        self.session.add(row)
        self.session.flush()
        return row.version

    def _create_undo(
        self,
        *,
        principal: Principal,
        action: str,
        permission: str,
        entity: str,
        entity_id: str | None,
        result: Any,
        version: int | None,
        risk_tier: RiskTier | str,
    ) -> AgentUndo | None:
        tier = RiskTier(risk_tier)
        if tier not in {RiskTier.LOW, RiskTier.MEDIUM}:
            return None
        if tier is RiskTier.MEDIUM and (entity_id is None or version is None):
            raise APIError(ErrorCode.VALIDATION_FAILED, "中风险动作必须提供实体 ID 和版本")
        if entity_id is None or version is None:
            return None
        if not self.undo_restore.supports(entity):
            raise APIError(ErrorCode.VALIDATION_FAILED, "该实体不支持撤销")
        if (
            not isinstance(result, dict)
            or "before" not in result
            or not isinstance(result["before"], dict)
        ):
            raise APIError(ErrorCode.VALIDATION_FAILED, "可撤销动作必须返回 before 对象")
        before = result["before"]
        reverse_action, reverse_payload, reverse_permission = _reverse_declaration(result)
        payload = UndoPayload(
            entity=entity,
            entityId=entity_id,
            action=action,
            permission=_catalog_permission(action, permission),
            before=before,
            actorId=str(principal.user_id) if principal.user_id else None,
            onBehalfOf=str(principal.on_behalf_of) if principal.on_behalf_of else None,
            actorType="agent" if principal.is_agent else "human",
            reverseAction=reverse_action,
            reversePayload=reverse_payload,
            reversePermission=reverse_permission,
        )
        row = AgentUndo(
            id=uuid4(),
            entity_type=entity,
            entity_id=entity_id,
            action_version=version,
            undo_payload_json=payload.model_dump(by_alias=True),
            deadline_at=datetime.now(UTC) + timedelta(hours=24),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def _can_undo(self, row: AgentUndo, principal: Principal) -> bool:
        UndoPayload.model_validate(row.undo_payload_json)
        return "agent_suggestion:create" in self.permission_service.current_permissions(principal)

    def _require_undo_target_access(
        self, row: AgentUndo, principal: Principal, payload: UndoPayload
    ) -> None:
        self.permission_service.require(principal, payload.permission, row.entity_id)
        if not _has_store_dimension(payload.entity):
            return
        if "storeId" not in payload.before:
            raise APIError(ErrorCode.VALIDATION_FAILED, "店铺维度实体撤销缺少 storeId")
        scope = self.permission_service.store_scope(principal, row.entity_type)
        if isinstance(scope, AllStores):
            return
        store_id = payload.before["storeId"]
        if UUID(str(store_id)) not in scope:
            raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")

    def _emit_events(
        self,
        context: dict[str, Any],
        action: str,
        result: Any,
        risk_tier: RiskTier | str,
        undo: AgentUndo | None = None,
    ) -> None:
        if context.get("entity_id") is None:
            return
        action_def = _CATALOG.action_by_id.get(action)
        if action_def is not None and action_def.kind == "查询":
            return
        event_type = _event_type(action)
        self.session.add(
            EntityEvent(
                id=uuid4(),
                event_type=event_type,
                entity_type=context["entity"],
                entity_id=context["entity_id"],
                action_id=action,
                payload_json={"result": _jsonable(result), "riskTier": RiskTier(risk_tier).value},
                created_at=datetime.now(UTC),
            )
        )
        if RiskTier(risk_tier) is RiskTier.MEDIUM:
            principal = context["principal"]
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
                        "riskTier": RiskTier(risk_tier).value,
                        "onBehalfOf": None
                        if principal.on_behalf_of is None
                        else str(principal.on_behalf_of),
                        "actorUserId": None
                        if principal.user_id is None
                        else str(principal.user_id),
                        "reversibleUntil": reversible_until.isoformat(),
                        "undoId": None if undo is None else str(undo.id),
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
        approval_id: UUID | None,
    ) -> None:
        identity, http, digest = execution_scope(principal, key=idempotency_key, action=action)
        self.session.add(
            ActionExecution(
                id=uuid4(),
                idempotency_key=idempotency_key,
                caller_identity=None if identity is None else identity.caller_identity,
                represented_user_id=None if identity is None else identity.represented_user_id,
                actor_key=None if identity is None else identity.actor_key,
                http_method=http.method,
                route_template=http.route_template,
                idempotency_scope_hash=digest,
                request_hash=_request_hash(request_payload),
                entity_type=entity,
                entity_id=entity_id,
                action_id=action,
                actor_type="agent" if principal.is_agent else "human",
                status=status,
                result_json=_jsonable(result),
                approval_id=approval_id,
                version=result.get("version") if isinstance(result, dict) else None,
                created_at=datetime.now(UTC),
            )
        )


def _call_business_action(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except TypeError as exc:
        raise APIError(ErrorCode.INTERNAL_ERROR, "业务动作必须是无参可调用对象") from exc


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {"value": value}


def _reverse_declaration(
    result: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if "undo" in result:
        spec = result["undo"]
    elif "undoPayload" in result:
        spec = result["undoPayload"]
    else:
        return None, None, None
    if "action" not in spec:
        raise APIError(ErrorCode.VALIDATION_FAILED, "撤销声明缺少动作")
    action = spec["action"]
    if "payload" in spec:
        payload = spec["payload"]
    else:
        payload = {key: value for key, value in spec.items() if key != "action"}
    if action in _CATALOG.action_by_id:
        return action, payload, _CATALOG.action_by_id[action].permission
    if "permission" not in payload:
        raise APIError(ErrorCode.VALIDATION_FAILED, "撤销反向动作未声明权限")
    return action, payload, payload["permission"]


def _catalog_permission(action: str, fallback: str) -> str:
    action_def = _CATALOG.action_by_id.get(action)
    if action_def is None:
        return fallback
    raw = action_def.raw.get("permission", action_def.permission)
    if isinstance(raw, list):
        if fallback not in raw:
            raise APIError(
                ErrorCode.VALIDATION_FAILED,
                "动作权限与目录不一致",
                details={"action": action, "permission": fallback},
            )
        return fallback
    return action_def.permission


def _with_undo(value: Any, undo: AgentUndo | None) -> Any:
    if undo is None:
        return value
    if isinstance(value, dict):
        return {**value, "undoId": str(undo.id)}
    return {"result": value, "undoId": str(undo.id)}


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
