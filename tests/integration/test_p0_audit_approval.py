from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from crosserp.api.errors import APIError, ErrorCode
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.log import append, verify_chain
from crosserp.auth.roles import Role
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import Approval, AuditLog, WorkflowRule
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
                approval_type="mapping",
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
                approval_type="voucher",
            )
            assert waiting.state == "awaiting_initiator"
            confirmed = ApprovalGatewayImpl(session).initiator_confirm(
                waiting.approval_id, principal=human, content={"confirm": True}
            )
            assert confirmed.state == "initiator_confirmed"
            rows = list(
                session.scalars(select(AuditLog).where(AuditLog.approval_id == waiting.approval_id))
            )
            assert any(
                item.actor_type == "agent" and item.agent_id == "agent-1" for item in rows
            )
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
                approval_type="voucher",
            )
            saved = session.get(Approval, row.approval_id)
            assert saved is not None
            assert row.state == "pending"
            assert str(approver.id) in saved.approver_ids
            from crosserp.api.errors import APIError

            with pytest.raises(APIError):
                ApprovalGatewayImpl(session).decide(
                    row.approval_id, principal=principal, decision="approve", comment="self"
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


def test_resolution_no_account_and_only_self_are_distinct(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            submitter = create_user(
                session, username="resolution-submitter", password="long-password-4"
            )
            grant_role(session, submitter.id, Role.FINANCE)
            session.add(
                WorkflowRule(
                    id=uuid4(),
                    approval_type="no-account",
                    version=1,
                    steps_json=[{"kind": "role", "role": "operator"}],
                    enabled=True,
                    updated_at=datetime.now(UTC),
                )
            )
            session.add(
                WorkflowRule(
                    id=uuid4(),
                    approval_type="only-self",
                    version=1,
                    steps_json=[{"kind": "specific_user", "userId": str(submitter.id)}],
                    enabled=True,
                    updated_at=datetime.now(UTC),
                )
            )
            principal = Principal(user_id=submitter.id)
            no_account = ApprovalGatewayImpl(session).submit(
                principal=principal,
                entity="no-account",
                action="create",
                payload={"x": 1},
                risk_tier="low",
                approval_type="no-account",
            )
            only_self = ApprovalGatewayImpl(session).submit(
                principal=principal,
                entity="only-self",
                action="create",
                payload={"x": 2},
                risk_tier="low",
                approval_type="only-self",
            )
            assert no_account.state == only_self.state == "auto_effective"
            assert no_account.resolution["reason"] == "no_account"
            assert only_self.resolution["reason"] == "only_self"
    finally:
        downgrade_base(url)


def test_multilevel_rule_skips_unresolvable_step_and_requires_each_live_step(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            submitter = create_user(session, username="multi-submit", password="long-password-5")
            approver = create_user(session, username="multi-approver", password="long-password-6")
            grant_role(session, approver.id, Role.FINANCE)
            session.add(
                WorkflowRule(
                    id=uuid4(),
                    approval_type="multi",
                    version=1,
                    steps_json=[
                        {"kind": "role", "role": "operator"},
                        {"kind": "role", "role": "finance"},
                    ],
                    enabled=True,
                    updated_at=datetime.now(UTC),
                )
            )
            row = ApprovalGatewayImpl(session).submit(
                principal=Principal(user_id=submitter.id),
                entity="multi",
                action="post",
                payload={"x": 1},
                risk_tier="high",
                approval_type="multi",
            )
            saved = session.get(Approval, row.approval_id)
            assert saved is not None
            assert row.state == "pending"
            assert saved.current_step == 1
            assert row.resolution["snapshot"][0]["skipped"] is True
            assert row.resolution["snapshot"][0]["reason"] == "no_account"
            approved = ApprovalGatewayImpl(session).decide(
                row.approval_id,
                principal=Principal(user_id=approver.id),
                decision="approve",
                comment="ok",
                content_hash=saved.content_hash,
            )
            assert approved.state == "approved"
            assert any(
                a.action == "approval.step_skipped" for a in session.scalars(select(AuditLog))
            )
    finally:
        downgrade_base(url)


def test_approval_rejects_payload_mismatch_and_represented_human(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            represented = create_user(session, username="represented", password="long-password-7")
            approver = create_user(
                session, username="represented-approver", password="long-password-8"
            )
            grant_role(session, approver.id, Role.FINANCE)
            session.add(
                WorkflowRule(
                    id=uuid4(),
                    approval_type="represented",
                    version=1,
                    steps_json=[{"kind": "role", "role": "finance"}],
                    enabled=True,
                    updated_at=datetime.now(UTC),
                )
            )
            agent = Principal(
                user_id=approver.id,
                actor_type=ActorType.AGENT,
                agent_id="agent-represented",
                on_behalf_of=represented.id,
                delegation_id="delegation-1",
                run_id="run-1",
                is_subagent=True,
                channel="mcp",
            )
            row = ApprovalGatewayImpl(session).submit(
                principal=agent,
                entity="represented",
                action="post",
                payload={"x": 1},
                risk_tier="high",
                approval_type="represented",
            )
            saved = session.get(Approval, row.approval_id)
            assert saved is not None
            assert saved.requested_by == str(represented.id)
            assert row.state == "pending"
            with pytest.raises(APIError) as self_error:
                ApprovalGatewayImpl(session).decide(
                    row.approval_id,
                    principal=Principal(user_id=represented.id),
                    decision="approve",
                    comment="self",
                    content_hash=saved.content_hash,
                )
            assert self_error.value.code == ErrorCode.FORBIDDEN
            with pytest.raises(APIError) as hash_error:
                ApprovalGatewayImpl(session).decide(
                    row.approval_id,
                    principal=Principal(user_id=approver.id),
                    decision="approve",
                    comment="bad hash",
                    content_hash="0" * 64,
                )
            assert hash_error.value.code == ErrorCode.PAYLOAD_HASH_MISMATCH
            audit = list(
                session.scalars(select(AuditLog).where(AuditLog.approval_id == row.approval_id))
            )
            submit_audit = audit[0]
            assert submit_audit.actor_type == "agent"
            assert submit_audit.agent_id == "agent-represented"
            assert submit_audit.on_behalf_of == str(represented.id)
            assert submit_audit.delegation_id == "delegation-1"
            assert submit_audit.run_id == "run-1"
            assert submit_audit.is_subagent is True
            assert submit_audit.channel == "mcp"
    finally:
        downgrade_base(url)
