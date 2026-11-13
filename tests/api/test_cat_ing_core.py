from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import CleansingIssue, ImportBatch, MappingRule, RawRow


def _login(client: TestClient, username: str, password: str = "password-123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def test_ingest_read_interfaces_page_and_include_counts(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="ingest-api", password="password-123", roles=(Role.ADMIN,)
        )
        rule = MappingRule(
            id=uuid4(),
            rule_key="order",
            rule_version="v1",
            kind="column",
            body_json={},
            status="active",
            verified=True,
            created_at=now,
        )
        batch = ImportBatch(
            id=uuid4(),
            connector_id="order",
            connector_version="v1",
            file_name="orders.csv",
            file_sha256="b" * 64,
            imported_at=now,
            row_count=1,
            status="cleansed",
            error_count=0,
            mapping_rule_version="v1",
            kind="order",
            created_by=user.id,
            received_at=now,
            landed_count=1,
            valid_count=1,
            counts_json={"landed": 1, "valid": 1, "duplicate": 0, "quarantined": 0, "projected": 0},
        )
        session.add_all([rule, batch])
        session.flush()
        raw = RawRow(
            batch_id=batch.id,
            row_no=2,
            payload_json={"email": "a@example.com", "orderId": "1"},
            sha256="c" * 64,
            received_at=now,
        )
        session.add(raw)
        session.flush()
        session.add(
            CleansingIssue(
                id=uuid4(),
                batch_id=batch.id,
                raw_record_id=raw.id,
                row_no=2,
                kind="invalid",
                field="orderId",
                message="bad",
                suggestion_json={},
                status="open",
                created_at=now,
            )
        )
        batch_id = batch.id

    _login(json_client, "ingest-api")
    listed = json_client.get("/api/v1/ingest/batches?page=1&pageSize=1")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["counts"]["landed"] == 1
    detail = json_client.get(f"/api/v1/ingest/batches/{batch_id}")
    assert detail.status_code == 200
    raw = json_client.get(f"/api/v1/ingest/batches/{batch_id}/raw-records")
    assert raw.status_code == 200
    assert raw.json()["items"][0]["payload"]["email"] == "***"
    issues = json_client.get(f"/api/v1/ingest/batches/{batch_id}/issues")
    assert issues.status_code == 200
    rules = json_client.get("/api/v1/ingest/mapping-rules")
    assert rules.status_code == 200
    assert rules.json()["items"][0]["version"] == "v1"


def test_ingest_unknown_batch_is_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username="ingest-404", password="password-123", roles=(Role.ADMIN,))
    _login(json_client, "ingest-404")
    response = json_client.get("/api/v1/ingest/batches/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
