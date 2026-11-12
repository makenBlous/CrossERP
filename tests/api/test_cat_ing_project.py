from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    EntityEvent,
    EntityVersion,
    ImportBatch,
    IngestProjection,
    MappingRule,
    RawRow,
    Sku,
    Store,
)


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "password-123"}
    )
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _batch(session: Session, *, user_id, status: str = "cleansed") -> ImportBatch:
    now = datetime.now(UTC)
    batch = ImportBatch(
        id=uuid4(),
        connector_id="sku",
        connector_version="v1",
        file_name="sku.json",
        file_sha256=uuid4().hex + uuid4().hex,
        imported_at=now,
        row_count=1,
        status=status,
        error_count=0,
        source="file",
        kind="sku",
        mapping_rule_version="v1",
        counts_json={},
        landed_count=1,
        valid_count=1,
        created_by=user_id,
        received_at=now,
    )
    session.add(batch)
    session.flush()
    session.add(
        RawRow(
            batch_id=batch.id,
            row_no=1,
            payload_json={
                "storeId": str(uuid4()),
                "platformSku": "P-1",
                "internalSku": "I-1",
                "title": "Demo",
            },
            received_at=now,
        )
    )
    return batch


def test_project_sku_writes_entity_version_and_is_idempotent(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-api", password="password-123", roles=(Role.ADMIN,)
        )
        store = Store(
            id=uuid4(), platform="amazon", marketplace="US", name="project", currency="USD"
        )
        session.add(store)
        rule = MappingRule(
            id=uuid4(),
            rule_key="sku",
            rule_version="v1",
            kind="sku",
            body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
            status="active",
            verified=True,
            created_at=now,
        )
        session.add(rule)
        batch = _batch(session, user_id=user.id)
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        raw.payload_json = {**raw.payload_json, "storeId": str(store.id)}
        batch_id = batch.id
    csrf = _login(json_client, "project-api")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "projected"
    assert body["projected"] == 1
    assert "undo" in body["items"][0]
    replay = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-1"},
    )
    assert replay.status_code == 200
    with Session(api_engine) as session:
        assert len(list(session.scalars(select(Sku)))) == 1
        assert len(list(session.scalars(select(EntityVersion)))) == 2


def test_supersede_emits_compensation_without_deleting_old_projection(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="supersede-api", password="password-123", roles=(Role.ADMIN,)
        )
        old = _batch(session, user_id=user.id, status="projected")
        new = _batch(session, user_id=user.id, status="cleansed")
        old_id, new_id = old.id, new.id
        session.add(
            IngestProjection(
                id=uuid4(),
                batch_id=old_id,
                raw_record_id=session.scalar(select(RawRow.id).where(RawRow.batch_id == old_id)),
                rule_version="v1",
                entity_type="Sku",
                entity_id=str(uuid4()),
                action_id="Sku.create",
                status="created",
                result_json={"posted": False},
                undo_payload_json={"action": "Sku.delete"},
                created_at=now,
            )
        )
    csrf = _login(json_client, "supersede-api")
    response = json_client.post(
        f"/api/v1/ingest/batches/{old_id}/supersede",
        json={"newBatchId": str(new_id)},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "supersede-1"},
    )
    assert response.status_code == 200, response.text
    with Session(api_engine) as session:
        assert session.get(ImportBatch, old_id).status == "superseded"
        assert session.get(ImportBatch, new_id).supersedes_id == old_id
        assert session.scalar(
            select(EntityEvent).where(
                EntityEvent.event_type == "ingest_batch.projection.compensated"
            )
        )


def test_project_unknown_batch_is_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username="project-404", password="password-123", roles=(Role.ADMIN,))
    csrf = _login(json_client, "project-404")
    response = json_client.post(
        "/api/v1/ingest/batches/00000000-0000-0000-0000-000000000000/project",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404
