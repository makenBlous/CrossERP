"""P0-03a 审批流程、审批人解析及统一网关。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.approval.state import ApprovalState, ConcurrentModification
from crosserp.audit.log import append
from crosserp.auth.roles import Role
from crosserp.db.schema import Approval, AppUser, UserRole, WorkflowRule
from crosserp.platform.principal import Principal


class ApproverResolver:
    """按规则逐步解析在职且具审批权限的账号。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve(
        self, approval_type: str, submitter: UUID | None, on_behalf_of: UUID | None
    ) -> dict[str, Any]:
        rule = self.session.scalar(
            select(WorkflowRule)
            .where(WorkflowRule.approval_type == approval_type, WorkflowRule.enabled.is_(True))
            .order_by(WorkflowRule.version.desc())
        )
        if rule is None:
            return {
                "reason": "no_rule",
                "ruleVersion": None,
                "steps": [],
                "approvers": [],
                "snapshot": [],
            }
        steps = rule.steps_json
        resolved_steps: list[dict[str, Any]] = []
        all_ids: list[str] = []
        for index, step in enumerate(steps):
            candidates = self._candidates(step)
            excluded = {str(x) for x in (submitter, on_behalf_of) if x is not None}
            candidate_ids = [str(u.id) for u in candidates]
            ids = [user_id for user_id in candidate_ids if user_id not in excluded]
            step_reason = None
            if not ids:
                step_reason = (
                    "only_self"
                    if candidate_ids and set(candidate_ids) <= excluded
                    else "no_account"
                )
            resolved_steps.append(
                {
                    "index": index,
                    "rule": step,
                    "candidates": candidate_ids,
                    "approvers": ids,
                    "skipped": not bool(ids),
                    "reason": step_reason,
                }
            )
            all_ids.extend(ids)
        reason = (
            None
            if all_ids
            else (
                "only_self"
                if resolved_steps and any(s["reason"] == "only_self" for s in resolved_steps)
                else "no_account"
            )
        )
        return {
            "reason": reason,
            "ruleVersion": rule.version,
            "steps": resolved_steps,
            "approvers": list(dict.fromkeys(all_ids)),
            "snapshot": resolved_steps,
        }

    def _candidates(self, step: dict[str, Any]) -> list[AppUser]:
        kind = step["kind"]
        approver_roles = (Role.ADMIN.value, Role.FINANCE.value)
        query = select(AppUser).where(
            AppUser.is_active.is_(True),
            AppUser.id.in_(select(UserRole.user_id).where(UserRole.role.in_(approver_roles))),
        )
        if kind in {"user", "specific_user"}:
            value = step.get("userId", step.get("user_id"))
            user = self.session.get(AppUser, UUID(str(value)))
            if user is None:
                return []
            if not user.is_active:
                return []
            role_exists = self.session.scalar(
                select(UserRole.user_id).where(
                    UserRole.user_id == user.id, UserRole.role.in_(approver_roles)
                )
            )
            return [user] if role_exists is not None else []
        if kind in {"role", "department_manager", "manager", "default"}:
            role = step.get("role", step.get("value"))
            if role:
                return list(
                    self.session.scalars(
                        query.where(
                            AppUser.id.in_(
                                select(UserRole.user_id).where(UserRole.role == str(role))
                            )
                        )
                    )
                )
            return list(self.session.scalars(query))
        raise APIError(ErrorCode.VALIDATION_ERROR, f"不支持的审批步骤类型: {kind}")


class ApprovalGatewayImpl:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.resolver = ApproverResolver(session)

    def submit(
        self,
        *,
        principal: Principal,
        entity: str,
        action: str,
        payload: Any,
        risk_tier: str,
        approval_type: str,
        request_id: str | None = None,
    ) -> Approval:
        payload_hash = hashlib.sha256(_canonical(payload).encode()).hexdigest()
        requested_by = principal.effective_user_id
        if requested_by is None:
            raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
        resolution = self.resolver.resolve(
            approval_type, principal.effective_user_id, principal.on_behalf_of
        )
        no_approver = not resolution["approvers"]
        high_or_money = risk_tier in {"high", "critical"} or entity.lower() in {
            "voucher",
            "payment",
            "ledger",
            "adjustment",
        }
        active_step = next((step for step in resolution["steps"] if not step["skipped"]), None)
        if no_approver and principal.is_agent and high_or_money:
            mode, state = "initiator_confirm", "awaiting_initiator"
        elif no_approver:
            mode, state = "no_approver_auto", "auto_effective"
        else:
            mode, state = "approver", "pending"
        row = Approval(
            id=uuid4(),
            target_type=entity,
            target_id=str(action),
            state=state,
            payload_hash=payload_hash,
            requested_by=str(requested_by),
            requested_at=datetime.now(UTC),
            approver=None,
            version=0,
            approval_type=approval_type,
            risk_tier=risk_tier,
            actor_type="agent" if principal.is_agent else "human",
            on_behalf_of=principal.on_behalf_of,
            resolution={
                "mode": mode,
                "reason": resolution["reason"],
                "ruleVersion": resolution["ruleVersion"],
                "snapshot": resolution["snapshot"],
                "note": _note(mode, resolution["reason"]),
            },
            content_hash=payload_hash,
            approver_ids=active_step["approvers"] if active_step else [],
            current_step=active_step["index"] if active_step else 0,
        )
        self.session.add(row)
        self.session.flush()
        append(
            self.session,
            "agent" if principal.is_agent else "human",
            "approval.submit",
            entity,
            str(row.id),
            None,
            {"state": state, "resolution": row.resolution},
            approval_id=row.id,
            actor_user_id=principal.user_id,
            agent_id=principal.agent_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            channel=principal.channel,
            entity_type=entity,
            entity_id=str(row.id),
            diff_json={"state": state},
            request_id=request_id,
            is_subagent=principal.is_subagent,
        )
        for step in resolution["steps"]:
            if step["skipped"]:
                append(
                    self.session,
                    "agent" if principal.is_agent else "human",
                    "approval.step_skipped",
                    entity,
                    str(row.id),
                    None,
                    {"step": step["index"], "reason": step["reason"]},
                    approval_id=row.id,
                    actor_user_id=principal.user_id,
                    agent_id=principal.agent_id,
                    on_behalf_of=principal.on_behalf_of,
                    delegation_id=principal.delegation_id,
                    run_id=principal.run_id,
                    is_subagent=principal.is_subagent,
                    channel=principal.channel,
                    entity_type=entity,
                    entity_id=str(row.id),
                    diff_json={"step": step["index"], "reason": step["reason"]},
                    request_id=request_id,
                )
        return row

    def decide(
        self,
        approval_id: UUID,
        *,
        principal: Principal,
        decision: str,
        comment: str | None,
        content_hash: str | None = None,
        request_id: str | None = None,
    ) -> Approval:
        if principal.is_agent:
            raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "智能体不能审批")
        row = self.session.get(Approval, approval_id)
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "审批单不存在")
        if row.state != ApprovalState.PENDING.value:
            raise APIError(ErrorCode.CONFLICT_VERSION, "审批单已处理")
        if content_hash is not None and content_hash != row.content_hash:
            raise APIError(ErrorCode.PAYLOAD_HASH_MISMATCH, "审批内容哈希不一致")
        if str(principal.user_id) in {
            row.requested_by,
            str(row.on_behalf_of) if row.on_behalf_of else "",
        }:
            raise APIError(ErrorCode.FORBIDDEN, "提交人或被代表人不能审批")
        assert row.approver_ids is not None
        allowed = {str(x) for x in row.approver_ids}
        if allowed and str(principal.user_id) not in allowed:
            raise APIError(ErrorCode.FORBIDDEN, "不是当前步骤审批人")
        if decision not in {"approve", "reject"}:
            raise APIError(ErrorCode.VALIDATION_ERROR, "decision 必须是 approve 或 reject")
        new_state = "approved" if decision == "approve" else "rejected"
        next_step: dict[str, Any] | None = None
        if new_state == "approved":
            assert row.resolution is not None
            snapshot = row.resolution["snapshot"]
            next_step = next(
                (
                    step
                    for step in snapshot
                    if step.get("index", -1) > row.current_step and not step.get("skipped")
                ),
                None,
            )
            if next_step is not None:
                new_state = "pending"
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(Approval)
                .where(
                    Approval.id == row.id,
                    Approval.version == row.version,
                    Approval.state == "pending",
                )
                .values(
                    state=new_state,
                    approver=str(principal.user_id),
                    decided_at=datetime.now(UTC),
                    comment=comment,
                    approver_ids=next_step["approvers"]
                    if next_step is not None
                    else row.approver_ids,
                    current_step=next_step["index"] if next_step is not None else row.current_step,
                    version=Approval.version + 1,
                )
            ),
        )
        if result.rowcount != 1:
            raise ConcurrentModification(row.id)
        self.session.refresh(row)
        append(
            self.session,
            "human",
            f"approval.{decision}",
            row.target_type,
            str(row.id),
            {"state": "pending"},
            {
                "state": new_state,
                "comment": comment,
                "step": row.current_step,
                "nextStep": next_step["index"] if next_step is not None else None,
            },
            approval_id=row.id,
            actor_user_id=principal.user_id,
            approver_id=principal.user_id,
            entity_type="Approval",
            entity_id=str(row.id),
            request_id=request_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
            diff_json={"state": new_state, "comment": comment},
        )
        return row

    def initiator_confirm(
        self,
        approval_id: UUID,
        *,
        principal: Principal,
        content: Any,
        request_id: str | None = None,
    ) -> Approval:
        if principal.is_agent:
            raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "仅真人可确认")
        row = self.session.get(Approval, approval_id)
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "审批单不存在")
        if row.state != "awaiting_initiator" or str(principal.user_id) != row.requested_by:
            raise APIError(ErrorCode.FORBIDDEN, "只有发起本人可确认")
        digest = hashlib.sha256(_canonical(content).encode()).hexdigest()
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(Approval)
                .where(Approval.id == row.id, Approval.version == row.version)
                .values(
                    state="initiator_confirmed",
                    initiator_confirmed_by=principal.user_id,
                    initiator_confirmed_at=datetime.now(UTC),
                    initiator_confirmation_hash=digest,
                    version=Approval.version + 1,
                )
            ),
        )
        if result.rowcount != 1:
            raise ConcurrentModification(row.id)
        self.session.refresh(row)
        append(
            self.session,
            "human",
            "approval.initiator_confirm",
            row.target_type,
            str(row.id),
            {"state": "awaiting_initiator"},
            {"state": "initiator_confirmed", "contentHash": digest},
            approval_id=row.id,
            actor_user_id=principal.user_id,
            entity_type="Approval",
            entity_id=str(row.id),
            diff_json={"contentHash": digest},
            request_id=request_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
        )
        return row

    def withdraw(
        self, approval_id: UUID, *, principal: Principal, request_id: str | None = None
    ) -> Approval:
        row = self.session.get(Approval, approval_id)
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "审批单不存在")
        if principal.is_agent or str(principal.user_id) != row.requested_by:
            raise APIError(ErrorCode.FORBIDDEN, "只有真人发起人可撤回")
        if row.state not in {"pending", "awaiting_initiator"}:
            raise APIError(ErrorCode.ILLEGAL_TRANSITION, "当前状态不能撤回")
        row.state = "withdrawn"
        row.version += 1
        append(
            self.session,
            "human",
            "approval.withdraw",
            row.target_type,
            str(row.id),
            {"state": "pending"},
            {"state": "withdrawn"},
            approval_id=row.id,
            actor_user_id=principal.user_id,
            request_id=request_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
            entity_type="Approval",
            entity_id=str(row.id),
            diff_json={"state": "withdrawn"},
        )
        return row


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _note(mode: str, reason: str) -> str:
    if mode == "approver":
        return "等待审批人审批"
    if mode == "initiator_confirm":
        return "需要发起人本人确认"
    return f"无审批人, 直接生效 ({reason})"


__all__ = ["ApprovalGatewayImpl", "ApproverResolver"]
