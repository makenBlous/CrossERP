from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.log import AuditLog
from crosserp.db.schema import Approval
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import ActorType, Principal


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

    with pytest.raises(RuntimeError, match="Session"):
        ActionDispatcher(
            permission_service=permission_service,
            audit_recorder=recorder,
            approval_gateway=gateway,
        )
    with pytest.raises(RuntimeError, match="AuditRecorder"):
        ActionDispatcher(
            session=session,
            permission_service=permission_service,
            approval_gateway=gateway,
        )
    with pytest.raises(RuntimeError, match="ApprovalGateway"):
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
        assert result["state"] == "awaiting_initiator"
        assert result["status"] == "awaiting_initiator"

    with Session(api_engine) as check:
        approval = check.scalar(select(Approval).order_by(Approval.requested_at.desc()))
        assert approval is not None
        audit = check.scalar(select(AuditLog).where(AuditLog.approval_id == approval.id))
        assert audit is not None


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
