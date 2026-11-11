# ruff: noqa: RUF002
"""CrossERP 自调度 worker、任务注册和周期调度。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session

from crosserp.audit.log import append
from crosserp.db.schema import Job

JobHandler = Callable[[dict[str, object]], str | None]


class UnknownJobKind(ValueError):
    """任务类型没有注册处理器。"""


class JobRegistry:
    """登记任务类型与其确定性处理器。"""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, kind: str, handler: JobHandler) -> JobHandler:
        if kind in self._handlers:
            raise ValueError(f"任务类型已注册: {kind}")
        self._handlers[kind] = handler
        return handler

    def resolve(self, kind: str) -> JobHandler:
        try:
            return self._handlers[kind]
        except KeyError as exc:
            raise UnknownJobKind(f"不认识的任务类型: {kind}") from exc


def _default_result(payload: dict[str, object]) -> str | None:
    result_ref = payload.get("resultRef")
    return str(result_ref) if result_ref is not None else None


DEFAULT_REGISTRY = JobRegistry()
for _kind in ("noop", "file_import", "agent_run"):
    DEFAULT_REGISTRY.register(_kind, _default_result)


def register_job(kind: str) -> Callable[[JobHandler], JobHandler]:
    """以装饰器登记一个任务处理器。"""

    def decorator(handler: JobHandler) -> JobHandler:
        DEFAULT_REGISTRY.register(kind, handler)
        return handler

    return decorator


def enqueue_job(
    session: Session,
    *,
    kind: str,
    created_by: UUID,
    payload: Mapping[str, object],
    created_at: datetime | None = None,
) -> Job:
    """把已登记或待校验的任务放入数据库队列。"""
    row = Job(
        kind=kind,
        status="queued",
        progress=Decimal("0"),
        payload_json=dict(payload),
        created_by=created_by,
        created_at=created_at or datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    append(
        session,
        "system",
        "Job.enqueue",
        "Job",
        str(row.id),
        None,
        {"status": row.status, "kind": row.kind},
    )
    return row


@dataclass
class _Schedule:
    name: str
    kind: str
    interval: timedelta
    created_by: UUID
    payload: dict[str, object]
    next_run_at: datetime


class JobScheduler:
    """按进程内配置周期把任务放入数据库队列。"""

    def __init__(self, registry: JobRegistry = DEFAULT_REGISTRY) -> None:
        self.registry = registry
        self._schedules: dict[str, _Schedule] = {}

    def register(
        self,
        name: str,
        *,
        kind: str,
        interval: timedelta,
        created_by: UUID,
        payload: Mapping[str, object],
        next_run_at: datetime,
    ) -> None:
        if name in self._schedules:
            raise ValueError(f"调度名称已注册: {name}")
        if interval <= timedelta(0):
            raise ValueError("调度周期必须大于零")
        self._schedules[name] = _Schedule(
            name=name,
            kind=kind,
            interval=interval,
            created_by=created_by,
            payload=dict(payload),
            next_run_at=next_run_at,
        )

    def enqueue_due(self, session: Session, *, now: datetime | None = None) -> list[Job]:
        current = now or datetime.now(UTC)
        created: list[Job] = []
        for schedule in self._schedules.values():
            while schedule.next_run_at <= current:
                created.append(
                    enqueue_job(
                        session,
                        kind=schedule.kind,
                        created_by=schedule.created_by,
                        payload=schedule.payload,
                        created_at=schedule.next_run_at,
                    )
                )
                schedule.next_run_at += schedule.interval
        return created


DEFAULT_SCHEDULER = JobScheduler(DEFAULT_REGISTRY)


def _claim(session: Session, job_id: UUID | None) -> Job | None:
    if job_id is None:
        candidate = session.scalar(
            select(Job.id).where(Job.status == "queued").order_by(Job.created_at, Job.id)
        )
    else:
        candidate = session.scalar(select(Job.id).where(Job.id == job_id, Job.status == "queued"))
    if candidate is None:
        return None
    started_at = datetime.now(UTC)
    result = cast(
        CursorResult[Any],
        session.execute(
            update(Job)
            .where(Job.id == candidate, Job.status == "queued")
            .values(status="running", started_at=started_at)
        ),
    )
    if result.rowcount != 1:
        return None
    row = session.get(Job, candidate)
    if row is None:
        raise RuntimeError(f"已领取的任务不存在: {candidate}")
    append(
        session,
        "system",
        "Job.start",
        "Job",
        str(row.id),
        {"status": "queued"},
        {"status": "running", "startedAt": started_at.isoformat()},
    )
    return row


def run_one(
    session: Session,
    *,
    job_id: UUID | None = None,
    registry: JobRegistry = DEFAULT_REGISTRY,
) -> Job | None:
    """原子领取并完成一个任务；未知 kind 和处理器异常都会留下失败记录。"""
    row = _claim(session, job_id)
    if row is None:
        return None
    payload = row.payload_json
    if not isinstance(payload, dict):
        raise TypeError("Job.payload_json 必须是对象")
    try:
        result_ref = registry.resolve(row.kind)(payload)
        row.progress = Decimal("1")
        row.status = "succeeded"
        row.result_ref = result_ref
    except Exception as exc:
        row.status = "failed"
        row.error = str(exc)
    row.finished_at = datetime.now(UTC)
    session.flush()
    append(
        session,
        "system",
        "Job.finish" if row.status == "succeeded" else "Job.fail",
        "Job",
        str(row.id),
        {"status": "running"},
        {
            "status": row.status,
            "progress": str(row.progress),
            "error": row.error,
            "resultRef": row.result_ref,
        },
    )
    return row


def run_worker(
    engine: Engine,
    *,
    job_id: UUID | None = None,
    registry: JobRegistry = DEFAULT_REGISTRY,
    scheduler: JobScheduler = DEFAULT_SCHEDULER,
) -> Job | None:
    with Session(engine, expire_on_commit=False) as session, session.begin():
        scheduler.enqueue_due(session)
        return run_one(session, job_id=job_id, registry=registry)


__all__ = [
    "DEFAULT_REGISTRY",
    "DEFAULT_SCHEDULER",
    "JobRegistry",
    "JobScheduler",
    "UnknownJobKind",
    "enqueue_job",
    "register_job",
    "run_one",
    "run_worker",
]
