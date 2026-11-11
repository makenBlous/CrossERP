# ruff: noqa: RUF002, RUF003
"""会话作废事件钩子，供 agent worker/P4 扩展。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Delegation, Job


def on_session_revoked(
    session: Session, session_token: str | None, *, reason: str = "logout"
) -> int:
    """作废委托并停止该会话发起的运行中任务，返回影响数量。"""
    if not session_token:
        return 0
    digest = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
    count = 0
    for delegation in session.scalars(
        select(Delegation).where(Delegation.session_id == digest, Delegation.status == "active")
    ):
        delegation.status = "revoked"
        delegation.revoke_reason = reason
        count += 1
    # P0 用 Job 作为最小运行登记；P4 的 agent run 可通过此钩子接入。
    for job in session.scalars(select(Job).where(Job.status == "running")):
        payload = job.payload_json if isinstance(job.payload_json, dict) else {}
        if payload.get("sessionId") == digest:
            job.status = "cancelled"
            job.error = "会话已作废"
            job.finished_at = datetime.now(UTC)
            count += 1
    return count


__all__ = ["on_session_revoked"]
