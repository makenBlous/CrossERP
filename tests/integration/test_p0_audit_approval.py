from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.log import append, verify_chain
from crosserp.auth.roles import Role
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import AuditLog, WorkflowRule
from crosserp.db.session import session_scope
from crosserp.platform.principal import ActorType, Principal

pytestmark = pytest.mark.db


def test_resolution_auto_effective_and_agent_confirmation(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            user = create_user(session, username="submitter", password="long-password-1")
            human = Principal(user_id=user.id)
            auto = ApprovalGatewayImpl(session).submit(
                principal=human,
                entity="mapping",
                action="create",
                payload={"x": 1},
                risk_tier="low",
            )
            assert auto.state == "auto_effective"
            assert auto.resolution["reason"] == "no_rule"
            agent = Principal(
                user_id=user.id,
                actor_type=ActorType.AGENT,
                agent_id="agent-1",
                on_behalf_of=user.id,
                channel="mcp",
            )
            waiting = ApprovalGatewayImpl(session).submit(
                principal=agent,
                entity="voucher",
                action="post",
                payload={"x": 2},
                risk_tier="high",
            )
            assert waiting.state == "awaiting_initiator"
            confirmed = ApprovalGatewayImpl(session).initiator_confirm(
                waiting.id, principal=human, content={"confirm": True}
            )
            assert confirmed.state == "initiator_confirmed"
            rows = list(session.scalars(select(AuditLog).where(AuditLog.approval_id == waiting.id)))
            assert any(row.actor_type == "agent" and row.agent_id == "agent-1" for row in rows)
            assert verify_chain(session).ok
    finally:
        downgrade_base(url)


def test_configured_approver_excludes_submitter_and_rejects_self_approval(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            submitter = create_user(session, username="submitter2", password="long-password-2")
            approver = create_user(session, username="approver2", password="long-password-3")
            grant_role(session, approver.id, Role.FINANCE)
            rule = WorkflowRule(
                id=uuid4(),
                approval_type="voucher",
                version=1,
                steps_json=[{"kind": "role", "role": "finance"}],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
            session.add(rule)
            principal = Principal(user_id=submitter.id)
            row = ApprovalGatewayImpl(session).submit(
                principal=principal,
                entity="voucher",
                action="post",
                payload={"x": 1},
                risk_tier="high",
            )
            assert row.state == "pending"
            assert str(approver.id) in row.approver_ids
            from crosserp.api.errors import APIError

            with pytest.raises(APIError):
                ApprovalGatewayImpl(session).decide(
                    row.id, principal=principal, decision="approve", comment="self"
                )
    finally:
        downgrade_base(url)


def test_new_audit_context_is_in_hash_chain(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = append(
                session,
                "agent",
                "tool.call",
                "AuditLog",
                "one",
                None,
                {"ok": True},
                agent_id="a-1",
                run_id="run-1",
                tool_call_id="call-1",
                channel="mcp",
                entity_type="AuditLog",
                entity_id="one",
                diff_json={"ok": True},
            )
            assert row.hash_version == 3
            assert verify_chain(session).ok
            row.channel = "web"
            assert verify_chain(session).ok is False
    finally:
        downgrade_base(url)
