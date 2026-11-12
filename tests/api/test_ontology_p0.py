from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api import install_api
from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.migrate import upgrade_head
from crosserp.db.repo.users import create_user
from crosserp.db.schema import ActionExecution, AuditLog, EntityEvent, EntityVersion, UserRole
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.ontology.catalog import load_catalog, validate_catalog
from crosserp.platform.approval import ApprovalSubmission
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.file_storage import FileStorage
from crosserp.platform.principal import ActorType, Principal, get_principal
from tests.api.conftest import TestApprovalGateway


class _UnitPermissionService:
    def require(self, principal, permission, _resource=None) -> None:
        if (
            permission not in {"public", "authenticated"}
            and permission not in principal.permissions
        ):
            raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

    def data_scope_filter(self, _principal, _entity):
        return {}

    def current_permissions(self, principal):
        return principal.permissions


def test_expected_version_conflict_and_idempotent_replay_do_not_write_twice() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        entity_id = uuid4()
        principal = Principal(user_id=uuid4(), permissions=frozenset({"store:write"}))
        session = Session(engine)
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=_UnitPermissionService(),
            audit_recorder=DefaultAuditRecorder(session),
            approval_gateway=TestApprovalGateway(),
        )
        with dispatcher.session.begin():
            first = dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                idempotency_key="onto-replay",
                business_action=lambda: {"before": {"v": 0}, "after": {"v": 1}},
            )
        with pytest.raises(APIError) as conflict, dispatcher.session.begin():
            dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                expected_version=0,
                business_action=lambda: {"after": {"v": 99}},
            )
        assert conflict.value.code is ErrorCode.CONFLICT_VERSION
        called: list[bool] = []
        with dispatcher.session.begin():
            replay = dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                idempotency_key="onto-replay",
                business_action=lambda: called.append(True),
            )
        with Session(engine) as session:
            assert first == replay
            assert called == []
            assert session.scalar(select(func.count()).select_from(EntityVersion)) == 1
        engine.dispose()


def test_subagent_scope_is_nested_and_rechecks_represented_permissions(api_engine) -> None:
    class MutablePermissions:
        def __init__(self) -> None:
            self.allowed = {"store:write"}

        def current_permissions(self, _principal: Principal) -> frozenset[str]:
            return frozenset(self.allowed)

        def require(self, principal: Principal, permission: str, resource: object = None) -> None:
            if permission not in self.allowed:
                raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

        def data_scope_filter(self, _principal: Principal, _entity: str) -> dict[str, object]:
            return {}

    service = MutablePermissions()
    session = Session(api_engine)
    represented = uuid4()
    child = Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        is_subagent=True,
        permissions=frozenset({"store:write"}),
        on_behalf_of=represented,
    )
    dispatcher = ActionDispatcher(
        session=session,
        permission_service=service,
        audit_recorder=DefaultAuditRecorder(session),
        approval_gateway=TestApprovalGateway(),
    )
    dispatcher.dispatch(
        principal=child,
        parent_permissions=frozenset({"store:write", "store:read"}),
        represented_permissions=frozenset({"store:write", "store:read"}),
        permission="store:write",
        risk_tier=RiskTier.LOW,
        action="Store.update",
        business_action=lambda: {"ok": True},
    )
    with pytest.raises(APIError) as expanded:
        dispatcher.dispatch(
            principal=child,
            parent_permissions=frozenset({"store:read"}),
            represented_permissions=frozenset({"store:write", "store:read"}),
            permission="store:write",
            risk_tier=RiskTier.LOW,
            action="Store.update",
            business_action=lambda: {"ok": True},
        )
    assert expanded.value.code is ErrorCode.DELEGATION_SCOPE_EXCEEDED
    service.allowed.clear()
    with pytest.raises(APIError) as revoked:
        dispatcher.dispatch(
            principal=child,
            parent_permissions=frozenset({"store:write"}),
            represented_permissions=frozenset({"store:write"}),
            permission="store:write",
            risk_tier=RiskTier.LOW,
            action="Store.update",
            business_action=lambda: {"ok": True},
        )
    assert revoked.value.code is ErrorCode.FORBIDDEN


def test_stage_failure_stops_pipeline_without_success_artifacts() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        session = Session(engine)
        seen: list[str] = []

        class Deny:
            def current_permissions(self, _principal: Principal) -> frozenset[str]:
                return frozenset()

            def require(self, *_args: object, **_kwargs: object) -> None:
                raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

            def data_scope_filter(self, *_args: object) -> dict[str, object]:
                return {}

        dispatcher = ActionDispatcher(
            session=session,
            permission_service=Deny(),
            audit_recorder=DefaultAuditRecorder(session),
            approval_gateway=TestApprovalGateway(),
            hooks={
                stage: (lambda stage=stage, **_: seen.append(stage))
                for stage in ActionDispatcher.STAGES
            },
        )
        with pytest.raises(APIError), session.begin():
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4()),
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=uuid4(),
                action="Store.update",
                business_action=lambda: seen.append("business"),
            )
        with Session(engine) as check:
            assert seen == ["identity_and_scope", "permission"]
            assert check.scalar(select(func.count()).select_from(EntityVersion)) == 0
            assert check.scalar(select(func.count()).select_from(ActionExecution)) == 0
            assert check.scalar(select(func.count()).select_from(AuditLog)) == 0
        engine.dispose()


def test_ai_off_and_degraded_modes_are_read_only(api_engine) -> None:
    principal = Principal(
        user_id=uuid4(), actor_type=ActorType.AGENT, permissions=frozenset({"store:write"})
    )
    for mode in ("off", "degraded"):
        session = Session(api_engine)
        dispatcher = ActionDispatcher(
            session=session,
            ai_mode=mode,
            permission_service=_UnitPermissionService(),
            audit_recorder=DefaultAuditRecorder(session),
            approval_gateway=TestApprovalGateway(),
        )
        with pytest.raises(APIError) as error:
            dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.LOW,
                action="Store.update",
                business_action=lambda: {"changed": True},
            )
        assert error.value.code is ErrorCode.AI_MODE_OFF
        assert dispatcher.dispatch(
            principal=principal,
            permission="authenticated",
            risk_tier=RiskTier.NONE,
            action="Store.get",
            business_action=lambda: {"changed": False},
        ) == {"changed": False}


def test_medium_action_keeps_reversible_preimage_and_daily_summary_event() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        session = Session(engine)
        entity_id = uuid4()
        with session.begin():
            ActionDispatcher(
                session=session,
                permission_service=_UnitPermissionService(),
                audit_recorder=DefaultAuditRecorder(session),
                approval_gateway=TestApprovalGateway(),
            ).dispatch(
                principal=Principal(
                    user_id=uuid4(), actor_type=ActorType.AGENT, permissions=frozenset({"x"})
                ),
                permission="x",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                payload={"before": {"name": "old"}},
                business_action=lambda: {"before": {"name": "old"}, "after": {"name": "new"}},
            )
        with Session(engine) as check:
            version = check.scalar(select(EntityVersion))
            digest = check.scalar(
                select(EntityEvent).where(EntityEvent.event_type == "notification.daily_summary")
            )
            assert version is not None and version.before_json == {"name": "old"}
            assert digest is not None
            assert digest.payload_json["notificationKind"] == "daily_summary"
            assert "reversibleUntil" in digest.payload_json
        engine.dispose()


def test_all_ontology_endpoints_have_success_and_404_paths_and_dry_run_is_read_only() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        app = FastAPI()
        install_api(app, engine, file_storage=FileStorage(Path(directory) / "files"))
        with Session(engine) as session, session.begin():
            allowed_user = create_user(
                session,
                username="ontology-owner",
                password="Ontology-test-password-123",
            )
            session.add(
                UserRole(
                    user_id=allowed_user.id, role="owner_manager", granted_at=datetime.now(UTC)
                )
            )
            allowed_user_id = allowed_user.id
        allowed = Principal(
            user_id=allowed_user_id,
            roles=frozenset({"owner_manager"}),
            permissions=frozenset({"authenticated"}),
        )
        entity_id = str(uuid4())
        with Session(engine) as session, session.begin():
            session.add(
                EntityVersion(
                    id=uuid4(),
                    entity_type="Store",
                    entity_id=entity_id,
                    version=1,
                    changed_at=datetime.now(UTC),
                    actor_type="human",
                    after_json={"name": "demo"},
                )
            )
        app.dependency_overrides[get_principal] = lambda: allowed
        with TestClient(app) as client:
            paths = [
                ("GET", "/api/v1/ontology/entity-types"),
                ("GET", "/api/v1/ontology/entity-types/Store"),
                ("GET", "/api/v1/ontology/actions"),
                ("GET", "/api/v1/ontology/event-types"),
                ("GET", f"/api/v1/entities/Store/{entity_id}/versions"),
                ("GET", f"/api/v1/entities/Store/{entity_id}/versions/1"),
                ("GET", f"/api/v1/entities/Store/{entity_id}/lineage"),
            ]
            for method, path in paths:
                response = client.request(method, path)
                assert response.status_code == 200, (method, path, response.text)
            assert client.get("/api/v1/entities/Store/does-not-exist/versions/1").status_code == 404
            assert client.get("/api/v1/entities/Store/does-not-exist/versions").status_code == 404
            assert client.get("/api/v1/entities/Store/does-not-exist/lineage").status_code == 404
            dry = client.post(
                "/api/v1/ontology/actions/Store.update/dry-run",
                json={"name": "new"},
                headers={"Idempotency-Key": "dry-run-only"},
            )
            assert dry.status_code == 200
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(EntityVersion)) == 1
            assert session.scalar(select(func.count()).select_from(ActionExecution)) == 0

        app.dependency_overrides[get_principal] = lambda: Principal(user_id=None)
        with TestClient(app) as client:
            unauthorized_paths = [
                "/api/v1/ontology/entity-types",
                "/api/v1/ontology/entity-types/Store",
                "/api/v1/ontology/actions",
                "/api/v1/ontology/event-types",
                f"/api/v1/entities/Store/{entity_id}/versions",
                f"/api/v1/entities/Store/{entity_id}/versions/1",
                f"/api/v1/entities/Store/{entity_id}/lineage",
            ]
            assert all(client.get(path).status_code == 401 for path in unauthorized_paths)
            assert client.post("/api/v1/ontology/actions/Store.update/dry-run").status_code == 401
            assert client.get("/api/v1/entities/Unknown/id/lineage").status_code == 401
        engine.dispose()


def test_catalog_loads_all_entities_and_rejects_missing_transition_action() -> None:
    assert (
        Path("src/crosserp/ontology/catalog/ontology-entities.yaml").read_bytes()
        == Path("docs/design/08/ontology-entities.yaml").read_bytes()
    )
    catalog = load_catalog()
    assert len(catalog.entity_types) == 166
    assert len(catalog.actions) >= 500
    broken = yaml.safe_load(
        Path("docs/design/08/ontology-entities.yaml").read_text(encoding="utf-8")
    )
    broken["entityTypes"][0]["actions"] = []
    with pytest.raises(ValueError, match="transition"):
        validate_catalog(broken)


def test_agent_high_risk_submits_approval_without_business_action(api_engine) -> None:
    submitted: list[dict[str, object]] = []

    class Gateway:
        def submit(self, **kwargs: object) -> ApprovalSubmission:
            submitted.append(kwargs)
            return ApprovalSubmission(
                approval_id=uuid4(),
                state="awaiting_initiator",
                resolution={"mode": "initiator_confirm", "reason": "no_rule"},
            )

    called: list[bool] = []
    principal = Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
        delegation_id="del-1",
        channel="agent",
    )
    session = Session(api_engine)
    result = ActionDispatcher(
        session=session,
        approval_gateway=Gateway(),
        permission_service=_UnitPermissionService(),
        audit_recorder=DefaultAuditRecorder(session),
    ).dispatch(
        principal=principal,
        permission="public",
        risk_tier=RiskTier.HIGH,
        entity="Voucher",
        action="Voucher.post",
        business_action=lambda: called.append(True),
    )
    assert result["approvalId"]
    assert result["state"] == "awaiting_initiator"
    assert result["status"] == "awaiting_initiator"
    assert result["resolution"]["mode"] == "initiator_confirm"
    assert called == []
    assert submitted[0]["action"] == "Voucher.post"


def test_dispatch_writes_entity_version_and_rolls_back_with_audit() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        principal = Principal(user_id=uuid4(), permissions=frozenset({"store:write"}))
        entity_id = uuid4()
        session = Session(engine)
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=_UnitPermissionService(),
            audit_recorder=DefaultAuditRecorder(session),
            approval_gateway=TestApprovalGateway(),
        )
        with dispatcher.session.begin():
            result = dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                business_action=lambda: {"before": {"name": "old"}, "after": {"name": "new"}},
            )
        with Session(engine) as session:
            row = session.scalar(
                select(EntityVersion).where(EntityVersion.entity_id == str(entity_id))
            )
            assert row is not None
            assert result["version"] == 1
            assert row.after_json == {"name": "new"}
        engine.dispose()


def test_ai_medium_has_no_count_limit_and_critical_is_rejected(api_engine) -> None:
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"store:write"}),
        actor_type=ActorType.AGENT,
    )
    calls: list[int] = []
    session = Session(api_engine)
    dispatcher = ActionDispatcher(
        session=session,
        permission_service=_UnitPermissionService(),
        audit_recorder=DefaultAuditRecorder(session),
        approval_gateway=TestApprovalGateway(),
    )
    # Medium actions must carry an entity id and before so an undo token can be issued.
    # Store.update is critical in the catalog. This test still passes medium to check the count rule.
    entity_id = str(uuid4())
    for index in range(8):
        dispatcher.dispatch(
            principal=principal,
            permission="store:write",
            risk_tier=RiskTier.MEDIUM,
            entity="Store",
            entity_id=entity_id,
            action="Store.update",
            business_action=lambda index=index: (
                calls.append(index) or {"before": {"name": "old"}, "after": {"name": str(index)}}
            ),
        )
    assert calls == list(range(8))
    with pytest.raises(APIError) as error:
        dispatcher.dispatch(
            principal=principal,
            permission="store:write",
            risk_tier=RiskTier.CRITICAL,
            action="Role.update",
            business_action=lambda: calls.append(99),
        )
    assert error.value.code is ErrorCode.AI_AUTONOMY_CAPPED
    assert 99 not in calls


def test_business_action_rejects_nonzero_argument_contract(api_engine) -> None:
    session = Session(api_engine)
    dispatcher = ActionDispatcher(
        session=session,
        permission_service=_UnitPermissionService(),
        audit_recorder=DefaultAuditRecorder(session),
        approval_gateway=TestApprovalGateway(),
    )
    principal = Principal(user_id=uuid4(), permissions=frozenset({"store:write"}))
    with pytest.raises(APIError) as error:
        dispatcher.dispatch(
            principal=principal,
            permission="store:write",
            risk_tier=RiskTier.LOW,
            action="Store.update",
            business_action=lambda _context: {"ok": True},
        )
    assert error.value.code is ErrorCode.INTERNAL_ERROR


def test_three_channels_have_same_result_and_denial(api_engine) -> None:
    session = Session(api_engine)
    dispatcher = ActionDispatcher(
        session=session,
        permission_service=_UnitPermissionService(),
        audit_recorder=DefaultAuditRecorder(session),
        approval_gateway=TestApprovalGateway(),
    )
    results = []
    for channel in ("web", "agent", "import"):
        results.append(
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4(), channel=channel),
                permission="authenticated",
                risk_tier=RiskTier.LOW,
                action="Store.create",
                business_action=lambda: {"ok": True},
            )
        )
    assert results == [{"ok": True}] * 3
    for channel in ("web", "agent", "import"):
        with pytest.raises(APIError) as error:
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4(), channel=channel),
                permission="store:write",
                risk_tier=RiskTier.LOW,
                action="Store.update",
                business_action=lambda: {"ok": True},
            )
        assert error.value.code is ErrorCode.FORBIDDEN
