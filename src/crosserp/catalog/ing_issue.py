"""清洗问题的处理、转交和转交记录查询。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import CleansingIssue, CleansingIssueTransfer, ImportBatch
from crosserp.platform.principal import Principal


def resolve(
    session: Session,
    issue: CleansingIssue,
    *,
    decision: str,
    reason: str | None,
    mapping: dict[str, Any] | None,
    handler: str,
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
    issue.handler = handler
    issue.resolution_json = {"decision": decision, "reason": reason, "mapping": mapping}
    issue.updated_at = datetime.now(UTC)
    issue.version += 1
    return {
        "id": str(issue.id),
        "status": issue.status,
        "decision": decision,
        "version": issue.version,
        "undo": previous,
    }


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
        "undo": previous,
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
    # 08 v4 §9.3 defines IngestBatch/CleansingIssue without storeId; this
    # chain is therefore company-wide. ActionDispatcher still invokes the
    # PermissionService data-scope protocol for the entity on every action.
    batch = session.get(ImportBatch, batch_id)
    issue = session.get(CleansingIssue, issue_id)
    if batch is None or issue is None or issue.batch_id != batch_id:
        raise not_found()
    return batch, issue


__all__ = ["escalate", "get_issue", "list_transfers", "resolve"]
