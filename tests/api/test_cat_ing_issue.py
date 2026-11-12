from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    Approval,
    AuditLog,
    CleansingIssue,
    CleansingIssueTransfer,
    EntityVersion,
    ImportBatch,
    RawRow,
)
from crosserp.platform.principal import ActorType, Principal


def _login(client: TestClient, username: str, password: str = "password-123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _issue(api_engine, username: str, *, money_impact: bool = False) -> tuple[UUID, UUID, UUID]:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username=username, password="password-123", roles=(Role.ADMIN,))
        batch = ImportBatch(
            id=uuid4(),
            connector_id="orders",
            connector_version="v1",
            file_name="orders.csv",
            file_sha256=uuid4().hex + "a" * 32,
            imported_at=now,
            row_count=1,
            status="cleansed",
            error_count=1,
            kind="order",
            mapping_rule_version="v1",
            created_by=user.id,
            received_at=now,
            landed_count=1,
            quarantined_count=1,
            counts_json={"landed": 1, "valid": 0, "duplicate": 0, "quarantined": 1, "projected": 0},
        )
        session.add(batch)
        session.flush()
        raw = RawRow(
            batch_id=batch.id, row_no=2, payload_json={"sku": "X"}, sha256="a" * 64, received_at=now
        )
        session.add(raw)
        session.flush()
        issue = CleansingIssue(
            id=uuid4(),
            batch_id=batch.id,
            raw_record_id=raw.id,
            row_no=2,
            kind="invalid",
            field="sku",
            message="SKU 无法映射",
            suggestion_json={"sku": "X"},
            status="open",
            money_impact=money_impact,
            created_at=now,
        )
        session.add(issue)
        return user.id, batch.id, issue.id


def test_resolve_ignore_requires_reason_and_is_idempotent(
    json_client: TestClient, api_engine
) -> None:
    _user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-resolve")
    csrf = _login(json_client, "ing-issue-resolve")
    headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "ing-issue-resolve-1"}
    payload = {"decision": "ignore", "reason": "人工确认是测试数据", "expectedVersion": 1}

    first = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json=payload,
        headers=headers,
    )
    replay = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json=payload,
        headers=headers,
    )

    assert first.status_code == replay.status_code == 200
    assert replay.json() == first.json()
    assert first.json()["status"] == "ignored"
    assert first.json()["version"] == 2
    with Session(api_engine) as session:
        row = session.get(CleansingIssue, issue_id)
        assert row is not None and row.status == "ignored" and row.version == 2
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "CleansingIssue.resolve")
            .order_by(AuditLog.seq.desc())
        )
        assert audit is not None and audit.actor_type == "human"


def test_resolve_expected_version_conflict_returns_409(json_client: TestClient, api_engine) -> None:
    _user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-version")
    csrf = _login(json_client, "ing-issue-version")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json={"decision": "ignore", "reason": "版本冲突", "expectedVersion": 99},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT_VERSION"


def test_escalate_creates_transfer_for_batch_uploader(json_client: TestClient, api_engine) -> None:
    user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-escalate")
    csrf = _login(json_client, "ing-issue-escalate")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/escalate",
        json={
            "reason": "自动处理未果",
            "attempts": [{"action": "补映射", "result": "没有唯一候选"}],
            "evidence": [{"rawRecordId": "1"}],
            "suggestion": {"next": "人工确认"},
            "expectedVersion": 1,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "escalated"
    with Session(api_engine) as session:
        row = session.get(CleansingIssue, issue_id)
        assert row is not None and row.assignee_user_id == user_id
        transfer = session.scalar(
            select(CleansingIssueTransfer).where(CleansingIssueTransfer.issue_id == issue_id)
        )
        assert transfer is not None and transfer.assignee_user_id == user_id


def test_agent_resolve_records_actor_context(
    json_client: TestClient, api_engine, monkeypatch
) -> None:
    user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-agent")
    csrf = _login(json_client, "ing-issue-agent")
    monkeypatch.setattr(
        "crosserp.api.routers._platform_common.get_principal",
        lambda _request: Principal(
            user_id=user_id,
            roles=frozenset({Role.ADMIN.value}),
            actor_type=ActorType.AGENT,
            agent_id="ing-agent",
            on_behalf_of=user_id,
            channel="mcp",
        ),
    )
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json={"decision": "duplicate", "reason": "指纹相同", "expectedVersion": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    with Session(api_engine) as session:
        version = session.scalar(
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == "CleansingIssue",
                EntityVersion.entity_id == str(issue_id),
            )
            .order_by(EntityVersion.version.desc())
        )
        assert (
            version is not None
            and version.actor_type == "agent"
            and version.on_behalf_of == user_id
        )


def test_agent_money_resolution_waits_for_human(
    json_client: TestClient, api_engine, monkeypatch
) -> None:
    user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-money", money_impact=True)
    csrf = _login(json_client, "ing-issue-money")
    monkeypatch.setattr(
        "crosserp.api.routers._platform_common.get_principal",
        lambda _request: Principal(
            user_id=user_id,
            roles=frozenset({Role.ADMIN.value}),
            actor_type=ActorType.AGENT,
            agent_id="ing-money-agent",
            on_behalf_of=user_id,
            channel="mcp",
        ),
    )
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json={"decision": "duplicate", "reason": "涉及金额", "expectedVersion": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["status"] in {"awaiting_initiator", "pending"}
    with Session(api_engine) as session:
        row = session.get(CleansingIssue, issue_id)
        assert row is not None and row.status == "open"
        approval = session.scalar(select(Approval).order_by(Approval.requested_at.desc()))
        assert approval is not None and approval.state in {"awaiting_initiator", "pending"}


def test_issue_write_is_hidden_without_import_permission(
    json_client: TestClient, api_engine
) -> None:
    _user_id, batch_id, issue_id = _issue(api_engine, "ing-issue-denied")
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="ing-issue-viewer", password="password-123", roles=(Role.VIEWER,)
        )
        assert user.id
    csrf = _login(json_client, "ing-issue-viewer")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/issues/{issue_id}/resolve",
        json={"decision": "ignore", "reason": "无权", "expectedVersion": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404
