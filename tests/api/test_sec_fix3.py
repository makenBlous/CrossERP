from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.log import AuditLog
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    ActionExecution,
    Approval,
    IamDataScopeRule,
    IamPermissionOverride,
    SkuCost,
)
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import ActorType, Principal, get_principal
from crosserp.web.app import create_app


class _PermissionService:
    def require(self, *_args: object, **_kwargs: object) -> None:
        return None

    def data_scope_filter(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return {}

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        return principal.permissions


def _principal() -> Principal:
    return Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="sec-fix3-agent",
        on_behalf_of=uuid4(),
        permissions=frozenset({"audit_log:write"}),
        channel="mcp",
    )


def test_install_api_does_not_keep_request_dispatcher_or_approval_gateway(json_client) -> None:
    assert not hasattr(json_client.app.state, "dispatcher")
    assert not hasattr(json_client.app.state, "approval_gateway")


def test_dispatcher_requires_session_audit_recorder_and_approval_gateway() -> None:
    permission_service = _PermissionService()
    session = Session()
    recorder = DefaultAuditRecorder(session)
    gateway = ApprovalGatewayImpl(session)

    with pytest.raises(TypeError, match="session"):
        ActionDispatcher(
            permission_service=permission_service,
            audit_recorder=recorder,
            approval_gateway=gateway,
        )
    with pytest.raises(TypeError, match="audit_recorder"):
        ActionDispatcher(
            session=session,
            permission_service=permission_service,
            approval_gateway=gateway,
        )
    with pytest.raises(TypeError, match="approval_gateway"):
        ActionDispatcher(
            session=session,
            permission_service=permission_service,
            audit_recorder=recorder,
        )
    session.close()


def test_agent_high_risk_approval_and_audit_commit_in_request_session(api_engine) -> None:
    principal = _principal()
    with Session(api_engine) as session, session.begin():
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=_PermissionService(),
            audit_recorder=DefaultAuditRecorder(session),
            approval_gateway=ApprovalGatewayImpl(session),
        )
        result = dispatcher.dispatch(
            principal=principal,
            permission="audit_log:write",
            risk_tier=RiskTier.HIGH,
            entity="RetentionPolicy",
            action="RetentionPolicy.update",
            business_action=lambda: {"retainDays": 30},
            request_id="sec-fix3-commit",
        )
    # submit 只返回 ApprovalSubmission. dispatcher 用 to_payload() 写审计和 HTTP 响应.
    assert result["approvalId"]
    assert result["status"] == result["state"] == "awaiting_initiator"
    assert "resolution" in result

    with Session(api_engine) as check:
        approval = check.scalar(select(Approval).order_by(Approval.requested_at.desc()))
        assert approval is not None
        audit = check.scalar(select(AuditLog).where(AuditLog.approval_id == approval.id))
        assert audit is not None


def test_http_agent_high_risk_returns_approval_payload_without_writing(api_database: str) -> None:
    app = create_app(api_database)
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"item:write", "item:read"}),
        actor_type=ActorType.AGENT,
        agent_id="sec-fix3-http",
        on_behalf_of=uuid4(),
    )
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(
            session, username=f"sec-fix3-{uuid4().hex}", password="Sec-fix3-password-123"
        )
        session.add_all(
            [
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="sec-fix3",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
                for permission in principal.permissions
            ]
        )
        session.add(
            IamDataScopeRule(
                name="sec-fix3 all stores",
                entity="*",
                scope_type="all",
                values=[],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        principal = replace(principal, user_id=user.id, on_behalf_of=user.id)
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/costs",
            json={
                "internalSku": "SEC-FIX3",
                "period": "2026-11",
                "unitCost": {"amountMinor": 10000, "currency": "CNY"},
                "source": "manual",
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["approvalId"]
    assert body["state"] in {"awaiting_initiator", "pending"}
    assert body["status"] == body["state"]
    with Session(app.state.database_engine) as check:
        assert check.scalar(select(SkuCost)) is None
        approval = check.scalar(select(Approval))
        assert approval is not None
        assert str(approval.id) == body["approvalId"]
        execution = check.scalar(select(ActionExecution))
        assert execution is not None
        json.dumps(execution.result_json)


def test_approval_and_audit_roll_back_with_request_transaction(api_engine) -> None:
    def failing_request() -> None:
        with Session(api_engine) as session, session.begin():
            dispatcher = ActionDispatcher(
                session=session,
                permission_service=_PermissionService(),
                audit_recorder=DefaultAuditRecorder(session),
                approval_gateway=ApprovalGatewayImpl(session),
            )
            dispatcher.dispatch(
                principal=_principal(),
                permission="audit_log:write",
                risk_tier=RiskTier.HIGH,
                entity="RetentionPolicy",
                action="RetentionPolicy.update",
                business_action=lambda: {"retainDays": 30},
            )
            raise APIError(ErrorCode.INTERNAL_ERROR, "业务失败")

    with pytest.raises(APIError, match="业务失败"):
        failing_request()

    with Session(api_engine) as check:
        assert check.scalar(select(Approval)) is None
        assert check.scalar(select(AuditLog)) is None
