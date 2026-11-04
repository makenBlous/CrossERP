"""审批单数据库读写。提交和事务由调用方负责。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Approval


def get_approval(session: Session, approval_id: UUID) -> Approval | None:
    """按 id 读取审批单。"""
    return session.get(Approval, approval_id)


def list_approvals(session: Session) -> list[Approval]:
    """按申请时间和 id 稳定列出审批单。"""
    return list(session.scalars(select(Approval).order_by(Approval.requested_at, Approval.id)))
