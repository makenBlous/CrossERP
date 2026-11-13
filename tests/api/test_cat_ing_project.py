from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import ErrorCode
from crosserp.auth.roles import Role
from crosserp.catalog.ingest_project import project_batch
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    EntityEvent,
    EntityVersion,
    IamDataScopeRule,
    ImportBatch,
    IngestProjection,
    MappingRule,
    RawRow,
    Sku,
    Store,
)
from crosserp.iam.scope import AllStores
from crosserp.platform.principal import ActorType, Principal


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
                "id": str(uuid4()),
                "storeId": str(uuid4()),
                "platformSku": "P-1",
                "internalSku": "I-1",
                "title": "Demo",
                "active": True,
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
        projected_id = str(raw.payload_json["id"])
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
        created = list(session.scalars(select(Sku)))
        assert len(created) == 1
        assert str(created[0].id) == projected_id
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


def test_project_ignores_row_permission_and_uses_action_permission(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-permission", password="password-123", roles=(Role.OPERATOR,)
        )
        store = Store(
            id=uuid4(), platform="amazon", marketplace="US", name="permission", currency="USD"
        )
        session.add(store)
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-permission",
                rule_version="permission-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "permission-v1"
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        raw.payload_json = {
            **raw.payload_json,
            "storeId": str(store.id),
            "permission": "authenticated",
        }
        batch_id = batch.id
    csrf = _login(json_client, "project-permission")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-permission-1"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.FORBIDDEN


def test_project_ignores_row_entity_and_action(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-spec", password="password-123", roles=(Role.ADMIN,)
        )
        store = Store(id=uuid4(), platform="amazon", marketplace="US", name="spec", currency="USD")
        session.add(store)
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-spec",
                rule_version="spec-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "spec-v1"
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        raw.payload_json = {
            **raw.payload_json,
            "storeId": str(store.id),
            "entityType": "Store",
            "action": "Store.create",
        }
        batch_id = batch.id
    csrf = _login(json_client, "project-spec")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-spec-1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["entityType"] == "Sku"
    assert response.json()["items"][0]["action"] == "Sku.create"


def test_project_rejects_unverified_mapping_rule(json_client: TestClient, api_engine) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-unverified", password="password-123", roles=(Role.ADMIN,)
        )
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-unverified",
                rule_version="unverified-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=False,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "unverified-v1"
        batch_id = batch.id
    csrf = _login(json_client, "project-unverified")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-unverified-1"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.UNVERIFIED_RULE_VERSION


def test_project_rejects_store_outside_data_scope_and_rolls_back(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    allowed_store = uuid4()
    blocked_store = uuid4()
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-scope", password="password-123", roles=(Role.ADMIN,)
        )
        session.add(
            Store(
                id=blocked_store,
                platform="amazon",
                marketplace="US",
                name="blocked",
                currency="USD",
            )
        )
        session.add(
            IamDataScopeRule(
                name="sku-scope",
                entity="Sku",
                scope_type="storeIds",
                values=[str(allowed_store)],
                updated_by=user.id,
                updated_at=now,
            )
        )
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-scope",
                rule_version="scope-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "scope-v1"
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        raw.payload_json = {**raw.payload_json, "storeId": str(blocked_store)}
        hidden_sku = uuid4()
        session.add(
            Sku(
                id=hidden_sku,
                store_id=blocked_store,
                platform_sku="BLOCKED",
                internal_sku="BLOCKED",
                title="blocked",
                aliases_json=[],
                active=True,
                created_at=now,
            )
        )
        batch_id = batch.id
    csrf = _login(json_client, "project-scope")
    hidden_read = json_client.get(f"/api/v1/catalog/skus/{hidden_sku}")
    assert hidden_read.status_code == 404
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-scope-1"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.DATA_SCOPE_DENIED
    with Session(api_engine) as session:
        assert session.scalar(select(Sku).where(Sku.platform_sku != "BLOCKED")) is None
        assert session.get(Sku, hidden_sku) is not None
        assert session.get(ImportBatch, batch_id).status == "cleansed"


def test_agent_money_projection_creates_approval_without_business_entity(api_engine) -> None:
    now = datetime.now(UTC)

    class PermissionService:
        def require(self, _principal, _permission, _resource=None) -> None:
            return None

        def data_scope_filter(self, _principal, _entity):
            return {}

        def store_scope(self, _principal, _entity):
            return AllStores()

        def current_permissions(self, principal):
            return principal.permissions

    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-agent-money", password="password-123", roles=(Role.ADMIN,)
        )
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="voucher-agent",
                rule_version="voucher-agent-v1",
                kind="voucher",
                body_json={"projection": {"entity": "Voucher", "action": "Voucher.from_order"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "voucher-agent-v1"
        principal = Principal(
            user_id=user.id,
            actor_type=ActorType.AGENT,
            agent_id="ingest-agent",
            on_behalf_of=user.id,
            permissions=frozenset({"journal_entry:create"}),
        )
        result = project_batch(
            session,
            batch.id,
            principal=principal,
            permission_service=PermissionService(),
            request_id="agent-money",
            idempotency_key="agent-money-1",
            payload={},
        )
        assert result["items"][0]["status"] == "awaiting_initiator"
        assert result["items"][0]["result"]["approvalId"]
        assert session.scalar(select(Sku)) is None


def test_project_rejects_store_dimension_without_store_id(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-no-store", password="password-123", roles=(Role.ADMIN,)
        )
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-no-store",
                rule_version="no-store-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "no-store-v1"
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        payload = dict(raw.payload_json)
        del payload["storeId"]
        raw.payload_json = payload
        batch_id = batch.id
    csrf = _login(json_client, "project-no-store")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-no-store-1"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_ERROR
    with Session(api_engine) as session:
        assert session.scalar(select(Sku)) is None
        assert session.get(ImportBatch, batch_id).status == "cleansed"


def test_project_rejects_missing_id_instead_of_generating_one(
    json_client: TestClient, api_engine
) -> None:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="project-no-id", password="password-123", roles=(Role.ADMIN,)
        )
        store = Store(id=uuid4(), platform="amazon", marketplace="US", name="no-id", currency="USD")
        session.add(store)
        session.add(
            MappingRule(
                id=uuid4(),
                rule_key="sku-no-id",
                rule_version="no-id-v1",
                kind="sku",
                body_json={"projection": {"entity": "Sku", "action": "Sku.create"}},
                status="active",
                verified=True,
                created_at=now,
            )
        )
        batch = _batch(session, user_id=user.id)
        batch.mapping_rule_version = "no-id-v1"
        raw = session.scalar(select(RawRow).where(RawRow.batch_id == batch.id))
        assert raw is not None
        payload = dict(raw.payload_json)
        del payload["id"]
        payload["storeId"] = str(store.id)
        raw.payload_json = payload
        batch_id = batch.id
    csrf = _login(json_client, "project-no-id")
    response = json_client.post(
        f"/api/v1/ingest/batches/{batch_id}/project",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "project-no-id-1"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_ERROR
    with Session(api_engine) as session:
        assert session.scalar(select(Sku)) is None
        assert session.get(ImportBatch, batch_id).status == "cleansed"
