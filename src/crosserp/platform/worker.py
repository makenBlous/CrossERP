# ruff: noqa: RUF002
"""CrossERP 自调度 worker 的最小同步执行入口。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crosserp.db.schema import Job


def run_one(session: Session, *, job_id: UUID | None = None) -> Job | None:
    """领取并完成一个任务；未知 kind 也会留下失败记录。"""
    statement = select(Job).where(Job.status == "queued").order_by(Job.created_at, Job.id)
    if job_id is not None:
        statement = statement.where(Job.id == job_id)
    row = session.scalar(statement)
    if row is None:
        return None
    row.status = "running"
    row.started_at = datetime.now(UTC)
    session.flush()
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    try:
        if row.kind not in {"noop", "file_import", "agent_run"}:
            raise ValueError(f"不认识的任务类型: {row.kind}")
        row.progress = Decimal("1")
        row.status = "succeeded"
        row.result_ref = str(payload.get("resultRef", "")) or None
    except Exception as exc:
        row.status = "failed"
        row.error = str(exc)
    row.finished_at = datetime.now(UTC)
    session.flush()
    return row


def run_worker(engine: Engine, *, job_id: UUID | None = None) -> Job | None:
    with Session(engine) as session, session.begin():
        return run_one(session, job_id=job_id)


__all__ = ["run_one", "run_worker"]
