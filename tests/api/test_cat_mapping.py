from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, IamDataScopeRule, IamPermissionOverride, SkuMapping, Store
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.principal import ActorType, Principal, get_principal
from crosserp.web.app import create_app


def _app(tmp_path: Path):
    url = sqlite_file_url(tmp_path / "mapping.db")
    app = create_app(url)
    return app, make_engine(url)


def _install(app, principal: Principal, store_id: str) -> Principal:
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"mapping-{uuid4().hex}",
            password="Mapping-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="mapping test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        session.add(
            IamDataScopeRule(
                id=uuid4(),
                name="mapping test scope",
                entity="SkuMapping",
                scope_type="storeIds",
                values=[store_id],
                updated_at=datetime.now(UTC),
            )
        )
        user_id = user.id
    effective = replace(
        principal,
        user_id=user_id,
        on_behalf_of=user_id if principal.is_agent else None,
    )
    app.dependency_overrides[get_principal] = lambda: effective
    return effective


def _seed(engine, *, platform_sku: str = "AMZ-1") -> tuple[str, str]:
    store_id = uuid4()
    mapping_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            Store(
                id=store_id,
                platform="amazon",
                marketplace="US",
                name="demo",
                currency="USD",
            )
        )
        session.flush()
        session.add(
            SkuMapping(
                id=mapping_id,
                store_id=store_id,
                platform_sku=platform_sku,
                internal_sku="INT-1",
                confidence="high",
                source="ai",
                state="suggested",
                version=0,
            )
        )
    return str(store_id), str(mapping_id)


def test_mapping_list_filters_and_paginates(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, _ = _seed(engine)
    _install(app, Principal(user_id=uuid4(), permissions=frozenset({"listing:read"})), store_id)
    with TestClient(app) as client:
        response = client.get("/api/v1/catalog/mappings?page=1&pageSize=1&q=AMZ")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["platformSku"] == "AMZ-1"
    engine.dispose()


def test_mapping_list_denies_without_permission_as_404(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    app.dependency_overrides[get_principal] = lambda: Principal(user_id=uuid4())
    with TestClient(app) as client:
        response = client.get("/api/v1/catalog/mappings")
    assert response.status_code == 404
    engine.dispose()


def test_human_create_is_idempotent_and_audited(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, _ = _seed(engine)
    _install(app, Principal(user_id=uuid4(), permissions=frozenset({"item:write"})), store_id)
    body = {
        "storeId": store_id,
        "platformSku": "AMZ-2",
        "internalSku": "INT-2",
        "confidence": "high",
    }
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/catalog/mappings", json=body, headers={"Idempotency-Key": "map-create-1"}
        )
        replay = client.post(
            "/api/v1/catalog/mappings", json=body, headers={"Idempotency-Key": "map-create-1"}
        )
    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == first.json()
    with Session(engine) as session:
        row = session.scalar(select(SkuMapping).where(SkuMapping.platform_sku == "AMZ-2"))
        audit = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()))
        assert row is not None and row.state == "confirmed" and row.version == 1
        assert audit is not None and audit.actor_type == "human"
    engine.dispose()


def test_agent_medium_create_contains_undo_payload(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, _ = _seed(engine)
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"item:write"}),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
        channel="mcp",
    )
    principal = _install(app, principal, store_id)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/mappings",
            json={"storeId": store_id, "platformSku": "AMZ-3", "internalSku": "INT-3"},
        )
    assert response.status_code == 201
    assert response.json()["undoPayload"]["action"] == "SkuMapping.delete"
    with Session(engine) as session:
        row = session.scalar(select(SkuMapping).where(SkuMapping.platform_sku == "AMZ-3"))
        audit = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()))
        assert row is not None and row.state == "suggested"
        assert audit is not None and audit.actor_type == "agent"
        assert audit.after_json["on_behalf_of"] == str(principal.on_behalf_of)
    engine.dispose()


def test_agent_high_confirm_submits_approval_without_mutating(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, mapping_id = _seed(engine)

    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"item:write"}),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
    )
    principal = _install(app, principal, store_id)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/mappings/confirm",
            json={"id": mapping_id, "expectedVersion": 0},
            headers={"Idempotency-Key": "map-confirm-1"},
        )
    assert response.status_code == 200
    assert response.json()["state"] == "awaiting_initiator"
    with Session(engine) as session:
        row = session.get(SkuMapping, UUID(mapping_id))
        assert row is not None and row.state == "suggested" and row.version == 0
        assert session.scalar(select(AuditLog).where(AuditLog.action == "approval.submit"))
    engine.dispose()


def test_human_high_confirm_submits_approval_without_mutating(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, mapping_id = _seed(engine)

    _install(app, Principal(user_id=uuid4(), permissions=frozenset({"item:write"})), store_id)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/mappings/confirm",
            json={"id": mapping_id, "expectedVersion": 0},
        )
    assert response.status_code == 200
    assert response.json()["state"] == "confirmed"
    with Session(engine) as session:
        row = session.get(SkuMapping, UUID(mapping_id))
        assert row is not None and row.state == "confirmed" and row.version == 1
        assert session.scalar(select(AuditLog).where(AuditLog.action == "SkuMapping.confirm"))
    engine.dispose()


def test_mapping_create_rejects_unknown_fields_with_validation_error(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, _ = _seed(engine)
    _install(app, Principal(user_id=uuid4(), permissions=frozenset({"item:write"})), store_id)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/mappings",
            json={
                "storeId": store_id,
                "platformSku": "AMZ-invalid",
                "internalSku": "INT-invalid",
                "status": "confirmed",
            },
        )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    engine.dispose()


def test_confirm_expected_version_conflict_and_missing_are_404_or_409(tmp_path: Path) -> None:
    app, engine = _app(tmp_path)
    store_id, mapping_id = _seed(engine)
    _install(app, Principal(user_id=uuid4(), permissions=frozenset({"item:write"})), store_id)
    with TestClient(app) as client:
        missing = client.post(
            "/api/v1/catalog/mappings/confirm", json={"id": str(uuid4()), "expectedVersion": 0}
        )
        conflict = client.post(
            "/api/v1/catalog/mappings/confirm",
            json={"id": mapping_id, "expectedVersion": 9},
        )
    assert missing.status_code == 404
    assert conflict.status_code == 409
    engine.dispose()
