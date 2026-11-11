from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api import install_api
from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.routers.agent_undo import _permission_service
from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import AgentUndo, AuditLog, EntityEvent, EntityVersion
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import ActorType, Principal, get_principal


class _Permissions:
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


def _agent(user_id=None) -> Principal:
    return Principal(
        user_id=user_id or uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="agent-undo",
        on_behalf_of=user_id or uuid4(),
        permissions=frozenset({"entity:write", "agent_suggestion:create"}),
    )


def test_medium_action_creates_undo_and_default_version_revert() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "undo.db")
        upgrade_head(url)
        engine = make_engine(url)
        session = Session(engine)
        owner = uuid4()
        principal = _agent(owner)
        entity_id = str(uuid4())
        dispatcher = ActionDispatcher(session=session, permission_service=_Permissions())
        with session.begin():
            result = dispatcher.dispatch(
                principal=principal,
                permission="entity:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                payload={"before": {"name": "old"}},
                business_action=lambda: {"before": {"name": "old"}, "after": {"name": "new"}},
            )
        assert result["undoId"]
        with session.begin():
            reverted = dispatcher.undo(
                result["undoId"],
                principal=Principal(
                    user_id=owner,
                    permissions=frozenset({"agent_suggestion:create"}),
                ),
            )
        assert reverted["undone"] is True
        with pytest.raises(APIError) as repeated, session.begin():
            dispatcher.undo(
                result["undoId"],
                principal=Principal(
                    user_id=owner,
                    permissions=frozenset({"agent_suggestion:create"}),
                ),
            )
        assert repeated.value.code is ErrorCode.UNDO_ALREADY_APPLIED
        with Session(engine) as check:
            undo = check.get(AgentUndo, UUID(result["undoId"]))
            versions = list(check.scalars(select(EntityVersion).order_by(EntityVersion.version)))
            audits = list(check.scalars(select(AuditLog).order_by(AuditLog.seq)))
            assert undo is not None and undo.undone_at is not None
            assert versions[-1].after_json == {"name": "old"}
            assert [row.action for row in audits][-2:] == ["Store.update", "AgentSuggestion.undo"]
        engine.dispose()


def test_undo_rejects_expired_repeated_concurrent_and_unauthorized() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "undo.db")
        upgrade_head(url)
        engine = make_engine(url)
        session = Session(engine)
        owner = uuid4()
        principal = _agent(owner)
        entity_id = str(uuid4())
        dispatcher = ActionDispatcher(session=session, permission_service=_Permissions())
        with session.begin():
            result = dispatcher.dispatch(
                principal=principal,
                permission="entity:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                payload={"before": {"name": "old"}},
                action="Store.update",
                business_action=lambda: {"before": {"name": "old"}, "after": {"name": "new"}},
            )
        with Session(engine) as change, change.begin():
            change.add(
                EntityVersion(
                    id=uuid4(),
                    entity_type="Store",
                    entity_id=entity_id,
                    version=2,
                    changed_at=datetime.now(UTC),
                    actor_type="human",
                    after_json={"name": "later"},
                )
            )
        with pytest.raises(APIError) as conflict, session.begin():
            dispatcher.undo(
                result["undoId"],
                principal=Principal(
                    user_id=owner,
                    permissions=frozenset({"agent_suggestion:create"}),
                ),
            )
        assert conflict.value.code is ErrorCode.CONFLICT_VERSION
        with Session(engine) as expire, expire.begin():
            row = expire.get(AgentUndo, UUID(result["undoId"]))
            assert row is not None
            row.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(APIError) as expired, session.begin():
            dispatcher.undo(
                result["undoId"],
                principal=Principal(
                    user_id=owner,
                    permissions=frozenset({"agent_suggestion:create"}),
                ),
            )
        assert expired.value.code is ErrorCode.UNDO_EXPIRED
        with pytest.raises(APIError) as denied, session.begin():
            dispatcher.undo(
                result["undoId"],
                principal=Principal(
                    user_id=uuid4(),
                    permissions=frozenset({"agent_suggestion:create"}),
                ),
            )
        assert denied.value.code is ErrorCode.NOT_FOUND
        engine.dispose()


def test_high_has_no_undo_and_critical_agent_is_blocked() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "undo.db")
        upgrade_head(url)
        engine = make_engine(url)
        session = Session(engine)
        principal = _agent()
        dispatcher = ActionDispatcher(session=session, permission_service=_Permissions())
        with pytest.raises(APIError) as blocked, session.begin():
            dispatcher.dispatch(
                principal=principal,
                permission="entity:write",
                risk_tier=RiskTier.CRITICAL,
                entity="Role",
                entity_id=str(uuid4()),
                action="Role.update",
                business_action=lambda: {"ok": True},
            )
        assert blocked.value.code is ErrorCode.AI_AUTONOMY_CAPPED
        with session.begin():
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4(), permissions=frozenset({"entity:write"})),
                permission="entity:write",
                risk_tier=RiskTier.HIGH,
                entity="Store",
                entity_id=str(uuid4()),
                action="Store.update",
                business_action=lambda: {"after": {"name": "high"}},
            )
        with Session(engine) as check:
            assert check.scalar(select(AgentUndo)) is None
        engine.dispose()


def test_daily_summary_counts_only_current_user_agent_actions() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "summary.db")
        upgrade_head(url)
        engine = make_engine(url)
        app = FastAPI()
        install_api(app, engine)
        owner = uuid4()
        principal = Principal(user_id=owner, permissions=frozenset({"agent_suggestion:read"}))
        with Session(engine) as session, session.begin():
            session.add(
                EntityEvent(
                    id=uuid4(),
                    event_type="notification.daily_summary",
                    entity_type="Store",
                    entity_id="s1",
                    action_id="Store.update",
                    payload_json={
                        "action": "Store.update",
                        "riskTier": "medium",
                        "actorUserId": str(owner),
                        "undoId": str(uuid4()),
                    },
                    created_at=datetime.now(UTC),
                )
            )
            session.add(
                EntityEvent(
                    id=uuid4(),
                    event_type="notification.daily_summary",
                    entity_type="Store",
                    entity_id="s2",
                    action_id="Store.update",
                    payload_json={"actorUserId": str(uuid4())},
                    created_at=datetime.now(UTC),
                )
            )
        app.dependency_overrides[get_principal] = lambda: principal
        app.dependency_overrides[_permission_service] = lambda: _Permissions()
        with TestClient(app) as client:
            response = client.get("/api/v1/agent/daily-summary")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["message"] == "AI 今天替你做了 1 件事"
        engine.dispose()
