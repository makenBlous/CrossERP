from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api import install_api
from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.routers.catalog_dedup import MergeRequest
from crosserp.db.migrate import upgrade_head
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AuditLog,
    DedupCandidate,
    DocumentLink,
    EntityEvent,
    EntityVersion,
    Sku,
    Store,
)
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.principal import ActorType, Principal, get_principal


class _Permissions:
    def __init__(self, allowed: set[str], scope: dict[str, object] | None = None) -> None:
        self.allowed = allowed
        self.scope = scope or {}

    def require(self, _principal: Principal, permission: str, _resource=None) -> None:
        if (
            permission not in self.allowed
            or (_principal.is_agent and permission not in _principal.permissions)
        ) and permission != "authenticated":
            raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

    def current_permissions(self, _principal: Principal) -> frozenset[str]:
        return frozenset(self.allowed)

    def data_scope_filter(self, _principal: Principal, _entity: str) -> dict[str, object]:
        return self.scope


def _app(
    tmp_path, *, allowed: set[str], scope: dict[str, object] | None = None
) -> tuple[FastAPI, object, Principal]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    url = sqlite_file_url(tmp_path / "dedup.db")
    upgrade_head(url)
    engine = make_engine(url)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        user = create_user(session, username=f"dedup-{uuid4().hex[:8]}", password="Dedup-test-123")
        user_id = user.id
    app = FastAPI()
    install_api(app, engine)
    app.state.permission_service = _Permissions(allowed, scope)
    principal = Principal(user_id=user_id, permissions=frozenset(allowed))
    app.dependency_overrides[get_principal] = lambda: principal
    return app, engine, principal


def _seed_skus(engine, principal: Principal) -> tuple[DedupCandidate, Sku, Sku, DocumentLink]:
    with Session(engine, expire_on_commit=False) as session, session.begin():
        store = Store(
            id=uuid4(),
            platform="amazon",
            marketplace="US",
            name="dedup-store",
            currency="USD",
        )
        session.add(store)
        session.flush()
        first = Sku(
            id=uuid4(),
            store_id=store.id,
            platform_sku="A",
            internal_sku="INT-A",
            title="主名称",
            active=True,
            aliases_json=["A"],
            source_refs_json=["raw:1"],
        )
        second = Sku(
            id=uuid4(),
            store_id=store.id,
            platform_sku="A-OLD",
            internal_sku="INT-A",
            title="旧名称",
            active=True,
            aliases_json=["A-OLD"],
            source_refs_json=["raw:2"],
        )
        candidate = DedupCandidate(
            id=uuid4(),
            entity_type="Sku",
            ids=[str(first.id), str(second.id)],
            reason="相同内部 SKU",
            confidence="high",
            status="open",
            version=1,
            provenance={"rawRecordIds": [1, 2], "actorType": "human"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        link = DocumentLink(
            id=uuid4(),
            from_type="OrderLine",
            from_id="order-1",
            to_type="Sku",
            to_id=str(second.id),
            relation="uses",
            created_at=datetime.now(UTC),
        )
        session.add_all([first, second, candidate, link])
        session.flush()
        return candidate, first, second, link


def test_dedup_list_is_paginated_and_searchable(tmp_path) -> None:
    app, engine, _principal = _app(tmp_path, allowed={"integration:read"})
    with Session(engine) as session, session.begin():
        now = datetime.now(UTC)
        for index in range(3):
            session.add(
                DedupCandidate(
                    id=uuid4(),
                    entity_type="Sku",
                    ids=[str(uuid4()), str(uuid4())],
                    reason=f"reason-{index}",
                    confidence="medium",
                    status="open",
                    version=1,
                    provenance={},
                    created_at=now,
                    updated_at=now,
                )
            )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingest/dedup-candidates?page=2&pageSize=1&q=reason-1&sort=-createdAt"
        )
    assert response.status_code == 200, response.text
    assert response.json()["pageSize"] == 1
    assert response.json()["total"] == 1
    engine.dispose()


def test_dedup_merge_preserves_aliases_sources_and_repoints_links(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path, allowed={"integration:read", "integration:write", "sku:write"}
    )
    candidate, first, second, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-merge-1"},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["canonicalId"] == str(first.id)
    assert set(payload["aliases"]) == {"A", "A-OLD"}
    assert set(payload["sourceRefs"]) == {"raw:1", "raw:2"}
    assert payload["undo"]["expiresAt"]
    with Session(engine) as session:
        canonical = session.get(Sku, first.id)
        duplicate = session.get(Sku, second.id)
        link = session.scalar(select(DocumentLink))
        version = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == "DedupCandidate",
                EntityVersion.entity_id == str(candidate.id),
            )
        )
        event = session.scalar(
            select(EntityEvent).where(EntityEvent.entity_type == "DedupCandidate")
        )
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "DedupCandidate.merge"))
        assert canonical is not None and canonical.aliases_json == ["A", "A-OLD"]
        assert duplicate is not None and duplicate.merged_into_id == str(first.id)
        assert link is not None and link.to_id == str(first.id)
        assert version is not None and version.actor_type == "human"
        assert event is not None and event.event_type == "dedupcandidate.merge.done"
        assert audit is not None and audit.actor_type == "human"
    engine.dispose()


def test_dedup_merge_is_idempotent_and_rejects_stale_version(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path, allowed={"integration:read", "integration:write", "sku:write"}
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        first_response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-merge-replay"},
        )
        replay = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-merge-replay"},
        )
        stale = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-merge-stale"},
        )
    assert first_response.status_code == 200
    assert replay.status_code == 200 and replay.json() == first_response.json()
    assert stale.status_code == 409
    engine.dispose()


def test_dedup_permissions_and_missing_candidate_use_required_statuses(tmp_path) -> None:
    denied_app, denied_engine, _principal = _app(tmp_path / "denied", allowed=set())
    with TestClient(denied_app) as client:
        assert client.get("/api/v1/ingest/dedup-candidates").status_code == 404
    denied_engine.dispose()

    app, engine, _principal = _app(
        tmp_path / "missing", allowed={"integration:read", "integration:write"}
    )
    with TestClient(app) as client:
        assert (
            client.post(
                f"/api/v1/ingest/dedup-candidates/{uuid4()}/merge",
                json={"expectedVersion": 1, "targetId": str(uuid4())},
            ).status_code
            == 404
        )
    engine.dispose()


def test_agent_medium_merge_keeps_actor_context_and_unknown_entity_is_explicit(tmp_path) -> None:
    app, engine, principal = _app(tmp_path, allowed={"integration:read", "integration:write"})
    agent = Principal(
        user_id=principal.user_id,
        actor_type=ActorType.AGENT,
        agent_id="dedup-agent",
        on_behalf_of=principal.user_id,
        permissions=frozenset({"integration:write"}),
        channel="mcp",
    )
    app.dependency_overrides[get_principal] = lambda: agent
    with Session(engine) as session, session.begin():
        candidate = DedupCandidate(
            id=uuid4(),
            entity_type="Supplier",
            ids=[str(uuid4()), str(uuid4())],
            reason="same",
            confidence="medium",
            status="open",
            version=1,
            provenance={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(candidate)
        candidate_id = candidate.id
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate_id}/merge",
            json={"expectedVersion": 1},
        )
    assert response.status_code in {400, 404, 422}
    with Session(engine) as session:
        row = session.get(DedupCandidate, candidate_id)
        assert row is not None and row.status == "open"
    engine.dispose()


def test_agent_medium_merge_records_on_behalf_of_audit(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path / "agent",
        allowed={"integration:read", "integration:write", "sku:write"},
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    agent = Principal(
        user_id=principal.user_id,
        actor_type=ActorType.AGENT,
        agent_id="dedup-agent",
        on_behalf_of=principal.user_id,
        permissions=frozenset({"integration:write", "sku:write"}),
        channel="mcp",
    )
    app.dependency_overrides[get_principal] = lambda: agent
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
        )
    assert response.status_code == 200, response.text
    with Session(engine) as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "DedupCandidate.merge"))
        version = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == "DedupCandidate",
                EntityVersion.entity_id == str(candidate.id),
            )
        )
        assert audit is not None and audit.actor_type == "agent"
        assert audit.on_behalf_of == str(principal.user_id)
        assert version is not None and version.actor_type == "agent"
        assert version.on_behalf_of == principal.user_id
    engine.dispose()


def test_merge_request_uses_camel_case_expected_version() -> None:
    request = MergeRequest.model_validate({"expectedVersion": 3, "targetId": str(uuid4())})
    assert request.expected_version == 3


def test_merge_requires_expected_version_and_rejects_canonical_id_alias(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path, allowed={"integration:read", "integration:write", "sku:write"}
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        missing = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"targetId": str(first.id)},
        )
        alias = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "canonicalId": str(first.id)},
        )
    assert missing.status_code == 422
    assert alias.status_code == 422
    engine.dispose()


def test_merge_requires_target_entity_write_permission(tmp_path) -> None:
    app, engine, principal = _app(tmp_path, allowed={"integration:read", "integration:write"})
    candidate, first, _, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
        )
    assert response.status_code == 404
    with Session(engine) as session:
        row = session.get(DedupCandidate, candidate.id)
        assert row is not None and row.status == "open"
    engine.dispose()


def test_dedup_scope_filters_candidates_and_merge_targets(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path,
        allowed={"integration:read", "integration:write", "sku:write"},
        scope={"scopes": ["store"], "filters": {"storeIds": [str(uuid4())]}},
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        listed = client.get("/api/v1/ingest/dedup-candidates")
        merged = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
        )
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    assert merged.status_code == 404
    with Session(engine) as session:
        row = session.get(DedupCandidate, candidate.id)
        assert row is not None and row.status == "open"
    engine.dispose()


def test_agent_permission_scope_is_checked_without_rebuilding_principal(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path, allowed={"integration:read", "integration:write", "sku:write"}
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    agent = Principal(
        user_id=principal.user_id,
        actor_type=ActorType.AGENT,
        agent_id="dedup-agent",
        on_behalf_of=principal.user_id,
        permissions=frozenset({"integration:write"}),
        channel="mcp",
    )
    app.dependency_overrides[get_principal] = lambda: agent
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
        )
    assert response.status_code == 404
    engine.dispose()


def test_idempotency_replay_runs_after_permission_check(tmp_path) -> None:
    app, engine, principal = _app(
        tmp_path, allowed={"integration:read", "integration:write", "sku:write"}
    )
    candidate, first, _, _ = _seed_skus(engine, principal)
    with TestClient(app) as client:
        first_response = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-permission-replay"},
        )
        app.state.permission_service = _Permissions(set())
        replay = client.post(
            f"/api/v1/ingest/dedup-candidates/{candidate.id}/merge",
            json={"expectedVersion": 1, "targetId": str(first.id)},
            headers={"Idempotency-Key": "dedup-permission-replay"},
        )
    assert first_response.status_code == 200
    assert replay.status_code == 404
    engine.dispose()
