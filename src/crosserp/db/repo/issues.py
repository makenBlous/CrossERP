"""异常清单只读查询。不改审计。不写业务表。"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import ImportBatch, Issue


def get_import_batch(session: Session, batch_id: UUID) -> ImportBatch | None:
    """按主键读取导入批次。"""
    return session.get(ImportBatch, batch_id)


def list_issues(
    session: Session,
    *,
    kind: str | None = None,
    batch_id: UUID | None = None,
) -> list[Issue]:
    """列出异常。批次筛选用 detail 里的 import_batch_id。避免方言 JSON 语法。"""
    statement = select(Issue).order_by(Issue.created_at, Issue.id)
    if kind is not None:
        statement = statement.where(Issue.kind == kind)
    found = list(session.scalars(statement))
    if batch_id is None:
        return found
    wanted = str(batch_id)
    return [item for item in found if batch_id_of(item) == wanted]


def count_issues_by_kind(session: Session, batch_id: UUID) -> dict[str, int]:
    """统计一个批次里各原因码的条数。"""
    counts: dict[str, int] = {}
    for item in list_issues(session, batch_id=batch_id):
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts


def batch_id_of(issue: Issue) -> str | None:
    """从 detail 取出批次 id。旧数据没有这个字段时返回空。"""
    value = detail_of(issue).get("import_batch_id")
    if isinstance(value, str) and value:
        return value
    return None


def detail_of(issue: Issue) -> dict[str, Any]:
    """把 detail_json 收成字典。坏数据不当异常抛出。"""
    raw = issue.detail_json
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(loaded, dict):
            return loaded
    return {}
