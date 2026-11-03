"""异常写入服务。统一原因码、状态和同一运行内去重。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
    )
