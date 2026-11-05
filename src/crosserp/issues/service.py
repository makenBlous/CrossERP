"""异常写入服务。统一原因码、状态和同一运行内去重。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.context import AuditContext, audited
from crosserp.core.enums import IssueKind, IssueStatus
from crosserp.db.repo.imports import insert_issue
from crosserp.db.schema import Issue
from crosserp.issues.catalog import definition


def open_issue(
    session: Session,
    kind: IssueKind | str,
    *,
    store_id: UUID | None,
    period: str | None,
    source_ref: str,
    detail: dict[str, Any],
    severity: str | None = None,
    settlement_line_id: UUID | None = None,
    order_line_id: UUID | None = None,
    recon_run_id: UUID | None = None,
) -> Issue:
    """打开异常; 同一原因码和 source_ref 已存在时复用旧记录。"""
    item = definition(kind)
    data = dict(detail)
    data.setdefault("source_ref", source_ref)
    if store_id is not None:
        data.setdefault("store_id", str(store_id))
    if period is not None:
        data.setdefault("period", period)
    for existing in session.scalars(select(Issue).where(Issue.kind == item.kind)):
        existing_detail = existing.detail_json
        if isinstance(existing_detail, dict) and existing_detail.get("source_ref") == source_ref:
            return existing
    return insert_issue(
        session,
        kind=item.kind,
        severity=item.severity if severity is None else severity,
        detail_json=data,
        status=IssueStatus.OPEN.value,
        created_at=datetime.now(UTC),
        settlement_line_id=settlement_line_id,
        order_line_id=order_line_id,
        recon_run_id=recon_run_id,
    )


_TRANSITIONS = {
    "open": {"explained", "resolved", "ignored"},
    "explained": {"resolved", "ignored", "open"},
    "resolved": {"open"},
    "ignored": {"open"},
}


def transition(
    session: Session,
    issue_id: UUID,
    to_status: IssueStatus | str,
    note: str | None,
    context: AuditContext | None = None,
) -> Issue:
    """改变异常状态并记录改前改后。"""
    issue = session.get(Issue, issue_id)
    if issue is None:
        raise LookupError(f"异常不存在: {issue_id}")
    target = IssueStatus(to_status).value
    if target not in _TRANSITIONS.get(issue.status, set()):
        raise ValueError(f"不允许从 {issue.status} 变为 {target}")
    if target in {IssueStatus.EXPLAINED.value, IssueStatus.IGNORED.value} and (
        note is None or len(note.strip()) < 5
    ):
        raise ValueError("已解释或忽略必须填写至少 5 个字的说明")
    if note is not None and len(note) > 2000:
        raise ValueError("说明超过 2000 个字符")
    before = {"status": issue.status, "resolution_note": issue.resolution_note}
    issue.status = target
    issue.resolution_note = note
    session.flush()
    with audited(
        session,
        context or AuditContext(),
        action="issue.transition",
        target_type="issue",
        target_id=str(issue.id),
        before=before,
        after={"status": issue.status, "resolution_note": issue.resolution_note},
    ):
        pass
    return issue
