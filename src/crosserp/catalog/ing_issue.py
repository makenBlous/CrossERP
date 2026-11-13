"""清洗问题的处理、转交和转交记录查询。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import CleansingIssue, CleansingIssueTransfer, ImportBatch, RawRow
from crosserp.iam.scope import AllStores
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.principal import Principal


def _handler_user_id(principal: Principal) -> str:
    user_id = principal.effective_user_id
    if user_id is None:
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    return str(user_id)


def _resolution_record(
    principal: Principal,
    *,
    decision: str,
    reason: str | None,
    mapping: dict[str, Any] | None,
) -> dict[str, Any]:
    record = {
        "decision": decision,
        "reason": reason,
        "mapping": mapping,
        "actorType": "agent" if principal.is_agent else "human",
        "actorId": _handler_user_id(principal),
        "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
    }
    if principal.is_agent:
        record["agentId"] = principal.agent_id
    return record


def resolve(
    session: Session,
    issue: CleansingIssue,
    *,
    decision: str,
    reason: str | None,
    mapping: dict[str, Any] | None,
    principal: Principal,
) -> dict[str, Any]:
    """执行一个清洗问题结论, 并返回可撤销信息。"""
    if issue.status not in {"open", "escalated"}:
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "当前状态不能处理清洗问题")
    if decision not in {"mapping", "duplicate", "ignore"}:
        raise APIError(ErrorCode.VALIDATION_ERROR, "decision 必须是 mapping、duplicate 或 ignore")
    if decision == "ignore" and not reason:
        raise APIError(ErrorCode.VALIDATION_ERROR, "忽略清洗问题必须填写 reason")
    if decision == "mapping" and not mapping:
        raise APIError(ErrorCode.VALIDATION_ERROR, "补映射必须填写 mapping")

    previous = {
        "status": issue.status,
        "handler": issue.handler,
        "resolution": issue.resolution_json,
        "version": issue.version,
    }
    issue.status = "ignored" if decision == "ignore" else "resolved"
    issue.handler = _handler_user_id(principal)
    issue.resolution_json = _resolution_record(
        principal, decision=decision, reason=reason, mapping=mapping
    )
    issue.updated_at = datetime.now(UTC)
    issue.version += 1
    return {
        "id": str(issue.id),
        "status": issue.status,
        "decision": decision,
        "version": issue.version,
        "before": previous,
        "undo": {"action": "CleansingIssue.resolve", **previous},
    }


def resolve_command(
    session: Session,
    issue: CleansingIssue,
    *,
    principal: Principal,
    decision: str,
    reason: str | None,
    mapping: dict[str, Any] | None,
    expected_version: int,
    request_id: str | None,
    payload: dict[str, Any],
    approval_gateway: ApprovalGateway,
) -> dict[str, Any]:
    """人处理涉钱问题时经执行器上的审批网关提交。免审批则生效, 其余结论直接执行。"""
    if issue.money_impact and not principal.is_agent:
        if issue.version != expected_version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "清洗问题版本已变化",
                details={"expectedVersion": expected_version, "actualVersion": issue.version},
            )
        approval = approval_gateway.submit(
            principal=principal,
            entity="CleansingIssue",
            action="CleansingIssue.resolve",
            payload=payload,
            risk_tier="high",
            approval_type="cleansingissue",
            request_id=request_id,
        )
        if approval.state == "auto_effective":
            applied = resolve(
                session,
                issue,
                decision=decision,
                reason=reason,
                mapping=mapping,
                principal=principal,
            )
            applied["approvalId"] = str(approval.approval_id)
            applied["approvalStatus"] = approval.state
            return applied
        return {
            "id": str(issue.id),
            "status": approval.state,
            "approvalId": str(approval.approval_id),
            "version": issue.version,
        }
    return resolve(
        session,
        issue,
        decision=decision,
        reason=reason,
        mapping=mapping,
        principal=principal,
    )


def escalate(
    session: Session,
    batch: ImportBatch,
    issue: CleansingIssue,
    *,
    principal: Principal,
    reason: str | None,
    attempts: list[Any],
    evidence: list[Any],
    suggestion: Any,
) -> dict[str, Any]:
    """把问题转交批次上传人, 并保存站内待办记录。"""
    if issue.status != "open":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "只有 open 状态的问题可以转交")
    if batch.created_by is None:
        raise APIError(ErrorCode.NOT_FOUND, "批次上传人不存在")
    previous = {
        "status": issue.status,
        "handler": issue.handler,
        "assigneeUserId": str(issue.assignee_user_id) if issue.assignee_user_id else None,
        "escalation": issue.escalation_json,
        "version": issue.version,
    }
    issue.status = "escalated"
    issue.handler = "uploader"
    issue.assignee_user_id = batch.created_by
    issue.agent_attempts += len(attempts) if attempts else 1
    issue.escalation_json = {
        "attempts": attempts,
        "evidence": evidence,
        "suggestion": suggestion,
        "reason": reason,
    }
    issue.updated_at = datetime.now(UTC)
    issue.version += 1
    transfer = CleansingIssueTransfer(
        id=uuid4(),
        batch_id=batch.id,
        issue_id=issue.id,
        assignee_user_id=batch.created_by,
        actor_type="agent" if principal.is_agent else "human",
        actor_id=principal.user_id,
        on_behalf_of=principal.on_behalf_of,
        attempts_json=attempts,
        evidence_json=evidence,
        suggestion_json=suggestion,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    session.add(transfer)
    session.flush()
    return {
        "id": str(issue.id),
        "status": issue.status,
        "assigneeUserId": str(issue.assignee_user_id),
        "agentAttempts": issue.agent_attempts,
        "transferId": str(transfer.id),
        "version": issue.version,
        "before": previous,
        "undo": {"action": "CleansingIssue.escalate", **previous},
    }


def list_transfers(session: Session, issue_id: UUID) -> Sequence[CleansingIssueTransfer]:
    """查询问题的转交记录, 供通知模块接入前的站内待办读取。"""
    return session.scalars(
        select(CleansingIssueTransfer)
        .where(CleansingIssueTransfer.issue_id == issue_id)
        .order_by(CleansingIssueTransfer.created_at.desc(), CleansingIssueTransfer.id.desc())
    ).all()


def get_issue(
    session: Session, batch_id: UUID, issue_id: UUID
) -> tuple[ImportBatch, CleansingIssue]:
    batch = session.get(ImportBatch, batch_id)
    issue = session.get(CleansingIssue, issue_id)
    if batch is None or issue is None or issue.batch_id != batch_id:
        raise not_found()
    return batch, issue


def issue_store_id(session: Session, issue: CleansingIssue) -> UUID | None:
    """店铺来自原件 payload 的 storeId。缺失或无效时无法证明在范围内。"""
    raw = session.get(RawRow, issue.raw_record_id)
    if raw is None or not isinstance(raw.payload_json, dict) or "storeId" not in raw.payload_json:
        return None
    value = raw.payload_json["storeId"]
    if not isinstance(value, str) or value == "":
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def issue_in_scope(
    session: Session, principal: Principal, permission_service: Any, issue: CleansingIssue
) -> bool:
    scope = permission_service.store_scope(principal, "CleansingIssue")
    store_id = issue_store_id(session, issue)
    if isinstance(scope, AllStores):
        return True
    if store_id is None:
        return False
    return store_id in scope


def require_issue_scope(
    session: Session,
    principal: Principal,
    permission_service: Any,
    issue: CleansingIssue,
    *,
    write: bool,
) -> None:
    if issue_in_scope(session, principal, permission_service, issue):
        return
    if write:
        raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")
    raise not_found()


__all__ = [
    "escalate",
    "get_issue",
    "issue_in_scope",
    "list_transfers",
    "require_issue_scope",
    "resolve",
    "resolve_command",
]
