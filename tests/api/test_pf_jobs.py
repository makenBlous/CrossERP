"""后台任务 Job、worker 和自调度验收。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.migrate import upgrade_head
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, Job
from crosserp.platform.worker import JobRegistry, JobScheduler, run_worker


def _login(client: TestClient, username: str, password: str = "password-123") -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def _user(engine, username: str):
    upgrade_head(str(engine.url))
    with Session(engine) as session, session.begin():
        return create_user(session, username=username, password="password-123").id


def _queued(engine, user_id, *, kind: str = "noop", payload: dict[str, object] | None = None):
    with Session(engine) as session, session.begin():
        row = Job(
            id=uuid4(),
            kind=kind,
            status="queued",
            progress=0,
            payload_json=payload or {},
            created_by=user_id,
            created_at=datetime.now(UTC),
        )
        session.add(row)
        session.flush()
        return row.id


def test_get_job_returns_contract_and_hides_other_user(json_client: TestClient, api_engine) -> None:
    owner = _user(api_engine, "job-owner")
    other = _user(api_engine, "job-other")
    row = _queued(api_engine, owner, payload={"resultRef": "batch-1"})

    _login(json_client, "job-other")
    hidden = json_client.get(f"/api/v1/jobs/{row}")
    assert hidden.status_code == 404

    _login(json_client, "job-owner")
    response = json_client.get(f"/api/v1/jobs/{row}")
    assert response.status_code == 200
    assert response.json()["id"] == str(row)
    assert response.json()["createdBy"] == str(owner)
    assert set(response.json()) >= {"id", "kind", "status", "progress", "createdBy", "createdAt"}
    assert other != owner


def test_worker_records_success_and_system_audit(api_engine) -> None:
    owner = _user(api_engine, "job-success")
    row = _queued(api_engine, owner, payload={"resultRef": "ok-ref"})

    result = run_worker(api_engine, job_id=row)

    assert result is not None
    assert result.status == "succeeded"
    assert result.progress == 1
    with Session(api_engine) as session:
        audit = session.scalar(
            select(AuditLog).where(AuditLog.target_id == str(row)).order_by(AuditLog.seq.desc())
        )
        assert audit is not None
        assert audit.actor_type == "system"


def test_worker_records_failure_and_unknown_kind(api_engine) -> None:
    owner = _user(api_engine, "job-failure")
    row = _queued(api_engine, owner, kind="unknown-kind")

    result = run_worker(api_engine, job_id=row)

    assert result is not None
    assert result.status == "failed"
    assert result.error == "不认识的任务类型: unknown-kind"


def test_two_workers_cannot_claim_same_job(api_engine) -> None:
    owner = _user(api_engine, "job-mutex")
    row = _queued(api_engine, owner)

    first = run_worker(api_engine, job_id=row)
    second = run_worker(api_engine, job_id=row)

    assert first is not None
    assert second is None


def test_scheduler_enqueues_due_jobs_by_interval(api_engine) -> None:
    owner = _user(api_engine, "job-scheduler")
    registry = JobRegistry()
    scheduler = JobScheduler(registry)
    start = datetime(2026, 11, 11, 0, 0, tzinfo=UTC)
    scheduler.register(
        "hourly-noop",
        kind="noop",
        interval=timedelta(hours=1),
        created_by=owner,
        payload={"resultRef": "scheduled"},
        next_run_at=start,
    )

    with Session(api_engine) as session, session.begin():
        first = scheduler.enqueue_due(session, now=start)
        second = scheduler.enqueue_due(session, now=start + timedelta(minutes=30))
        third = scheduler.enqueue_due(session, now=start + timedelta(hours=1))
        first_id = first[0].id

    assert len(first) == 1
    assert second == []
    assert len(third) == 1
    with Session(api_engine) as session:
        assert session.scalar(select(Job).where(Job.id == first_id)).status == "queued"
