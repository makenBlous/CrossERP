"""P0 审计与审批中心 23 个 JSON API 的成功、拒绝和资源不存在测试。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.log import append, verify_chain
from crosserp.auth.roles import Role
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import (
    Approval,
    AppUser,
    AuditAlert,
    AuditLog,
    WorkflowRule,
)
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.ledger.write_service import ApprovalRequired, export
from crosserp.platform.principal import ActorType, Principal, get_principal


def _principal(user_id: UUID | None = None, role: str = "admin") -> Principal:
    return Principal(user_id=user_id or uuid4(), roles=frozenset({role}))


def _user(session: Session, username: str, *roles: Role) -> Any:
    user = create_user(session, username=username, password="Api-test-password-123")
    for role in roles:
        grant_role(session, user.id, role)
    return user


def _audit_row(session: Session, *, actor_type: str = "human", **context: Any) -> AuditLog:
    return append(
        session,
        actor_type,
        "test.action",
        "TestEntity",
        str(uuid4()),
        None,
        {"ok": True},
        actor_user_id=context.pop("actor_user_id", uuid4()),
        self_approved=False,
        entity_type="TestEntity",
        entity_id="trace-1",
        **context,
    )


def _rule(session: Session, approval_type: str, *, role: str = "finance") -> WorkflowRule:
    row = WorkflowRule(
        id=uuid4(),
        approval_type=approval_type,
        version=1,
        steps_json=[{"kind": "role", "role": role}],
        enabled=True,
        updated_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row


def _pending_approval(api_engine, *, approval_type: str = "api-voucher") -> tuple[UUID, UUID, UUID]:
    with Session(api_engine) as session, session.begin():
        submitter = _user(session, f"submitter-{uuid4().hex[:8]}", Role.OPERATOR)
        approver = _user(session, f"approver-{uuid4().hex[:8]}", Role.FINANCE)
        _rule(session, approval_type)
        row = ApprovalGatewayImpl(session).submit(
            principal=Principal(user_id=submitter.id),
            entity="voucher",
            action="post",
            payload={"value": 1},
            risk_tier="high",
            approval_type=approval_type,
        )
        return UUID(str(row.id)), UUID(str(submitter.id)), UUID(str(approver.id))


def _awaiting_initiator(api_engine) -> tuple[UUID, UUID, Principal]:
    with Session(api_engine) as session, session.begin():
        submitter = _user(session, f"agent-submit-{uuid4().hex[:8]}", Role.OPERATOR)
        agent = Principal(
            user_id=submitter.id,
            actor_type=ActorType.AGENT,
            agent_id="api-agent",
            on_behalf_of=submitter.id,
            delegation_id="delegation-api",
            run_id="run-api",
            is_subagent=True,
            channel="mcp",
        )
        row = ApprovalGatewayImpl(session).submit(
            principal=agent,
            entity="voucher",
            action="post",
            payload={"value": 2},
            risk_tier="high",
            approval_type="api-no-rule",
        )
        return UUID(str(row.id)), UUID(str(submitter.id)), agent


@pytest.fixture
def use_principal(json_client: TestClient):
    def set_principal(principal: Principal) -> None:
        if principal.user_id is not None:
            with Session(json_client.app.state.database_engine) as session, session.begin():
                user = session.get(AppUser, principal.user_id)
                if user is None:
                    user = AppUser(
                        id=principal.user_id,
                        username=f"principal-{principal.user_id.hex[:12]}",
                        display_name="测试身份",
                        password_hash="x",
                        is_active=True,
                        failed_logins=0,
                        locked_until=None,
                        password_changed_at=datetime.now(UTC),
                        must_change_password=False,
                        created_at=datetime.now(UTC),
                        permission_version=0,
                    )
                    session.add(user)
                    session.flush()
                for role in principal.roles:
                    if role in Role._value2member_map_:
                        grant_role(session, principal.user_id, role)
        json_client.app.dependency_overrides[get_principal] = lambda: principal

    yield set_principal
    json_client.app.dependency_overrides.pop(get_principal, None)


@pytest.mark.parametrize(
    ("path", "method", "kwargs", "permission_role"),
    [
        ("/api/v1/audit/logs", "get", {}, "admin"),
        ("/api/v1/audit/chain", "get", {}, "admin"),
        ("/api/v1/audit/security-events", "get", {}, "admin"),
        ("/api/v1/audit/alerts", "get", {}, "admin"),
        ("/api/v1/audit/retention", "get", {}, "admin"),
        ("/api/v1/audit/retention/archive-runs", "get", {}, "admin"),
        ("/api/v1/approvals", "get", {}, "admin"),
        ("/api/v1/approvals/types", "get", {}, "admin"),
        ("/api/v1/workflow/rules/resolve", "get", {}, "admin"),
        ("/api/v1/workflow/rules", "get", {}, "admin"),
    ],
)
def test_read_endpoints_allow_role_and_reject_viewer(
    json_client: TestClient,
    use_principal,
    path: str,
    method: str,
    kwargs: dict[str, Any],
    permission_role: str,
) -> None:
    use_principal(_principal(role=permission_role))
    response = getattr(json_client, method)(path, **kwargs)
    assert response.status_code == 200

    use_principal(_principal(role="guest"))
    denied = getattr(json_client, method)(path, **kwargs)
    assert denied.status_code == 404


@pytest.mark.parametrize(
    ("path", "method", "kwargs"),
    [
        ("/api/v1/audit/verify", "post", {}),
        ("/api/v1/audit/exports", "post", {"json": {"format": "jsonl"}}),
        ("/api/v1/audit/retention", "put", {"json": {"chain": "audit_log", "retainDays": 30}}),
        ("/api/v1/audit/retention/archive", "post", {}),
    ],
)
def test_audit_write_endpoints_allow_admin_and_reject_viewer(
    json_client: TestClient,
    use_principal,
    path: str,
    method: str,
    kwargs: dict[str, Any],
) -> None:
    use_principal(_principal(role="admin"))
    response = getattr(json_client, method)(path, **kwargs)
    assert response.status_code == 200

    use_principal(_principal(role="guest"))
    denied = getattr(json_client, method)(path, **kwargs)
    assert denied.status_code == 404


def test_audit_log_get_allows_auditor_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    with Session(api_engine) as session, session.begin():
        row = _audit_row(session)
        row_id = row.id
    use_principal(_principal(role="auditor"))
    assert json_client.get(f"/api/v1/audit/logs/{row_id}").status_code == 200
    use_principal(_principal(role="guest"))
    assert json_client.get(f"/api/v1/audit/logs/{row_id}").status_code == 404
    use_principal(_principal(role="auditor"))
    assert json_client.get(f"/api/v1/audit/logs/{uuid4()}").status_code == 404


def test_agent_trace_missing_resource_returns_404(json_client: TestClient, use_principal) -> None:
    use_principal(_principal(role="admin"))
    assert json_client.get(f"/api/v1/audit/agent-trace/{uuid4()}").status_code == 404


def test_agent_trace_allows_admin_rejects_guest_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    with Session(api_engine) as session, session.begin():
        _audit_row(session)
    use_principal(_principal(role="admin"))
    assert json_client.get("/api/v1/audit/agent-trace/trace-1").status_code == 200
    use_principal(_principal(role="guest"))
    assert json_client.get("/api/v1/audit/agent-trace/trace-1").status_code == 404


def test_audit_export_download_allows_auditor_rejects_viewer_and_returns_404(
    json_client: TestClient, use_principal
) -> None:
    use_principal(_principal(role="auditor"))
    created = json_client.post("/api/v1/audit/exports", json={"format": "jsonl"})
    assert created.status_code == 200
    export_id = created.json()["id"]
    assert json_client.get(f"/api/v1/audit/exports/{export_id}/download").status_code == 200
    use_principal(_principal(role="guest"))
    assert json_client.get(f"/api/v1/audit/exports/{export_id}/download").status_code == 404
    use_principal(_principal(role="auditor"))
    assert json_client.get(f"/api/v1/audit/exports/{uuid4()}/download").status_code == 404


def test_audit_alert_resolve_allows_admin_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    with Session(api_engine) as session, session.begin():
        alert = AuditAlert(
            id=uuid4(),
            kind="test",
            status="open",
            detail_json={"source": "api"},
            created_at=datetime.now(UTC),
        )
        session.add(alert)
        session.flush()
        alert_id = alert.id
    use_principal(_principal(role="admin"))
    assert json_client.post(f"/api/v1/audit/alerts/{alert_id}/resolve").status_code == 200
    use_principal(_principal(role="guest"))
    assert json_client.post(f"/api/v1/audit/alerts/{alert_id}/resolve").status_code == 404
    use_principal(_principal(role="admin"))
    assert json_client.post(f"/api/v1/audit/alerts/{uuid4()}/resolve").status_code == 404


def test_approval_get_allows_admin_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, _, _ = _pending_approval(api_engine)
    use_principal(_principal(role="admin"))
    assert json_client.get(f"/api/v1/approvals/{row_id}").status_code == 200
    use_principal(_principal(role="guest"))
    assert json_client.get(f"/api/v1/approvals/{row_id}").status_code == 404
    use_principal(_principal(role="admin"))
    assert json_client.get(f"/api/v1/approvals/{uuid4()}").status_code == 404


def test_approval_decide_allows_current_approver_rejects_operator_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, _, approver_id = _pending_approval(api_engine, approval_type="api-decide")
    use_principal(_principal(approver_id, "finance"))
    response = json_client.post(
        f"/api/v1/approvals/{row_id}/decide",
        json={"decision": "approve"},
    )
    assert response.status_code == 200

    row2_id, submitter_id, _ = _pending_approval(api_engine, approval_type="api-decide-denied")
    use_principal(_principal(submitter_id, "operator"))
    assert (
        json_client.post(
            f"/api/v1/approvals/{row2_id}/decide", json={"decision": "approve"}
        ).status_code
        == 404
    )
    use_principal(_principal(role="admin"))
    assert (
        json_client.post(
            f"/api/v1/approvals/{uuid4()}/decide", json={"decision": "approve"}
        ).status_code
        == 404
    )


def test_approval_decide_rejects_stale_payload_hash(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, _, approver_id = _pending_approval(api_engine, approval_type="api-hash")
    use_principal(_principal(approver_id, "finance"))
    response = json_client.post(
        f"/api/v1/approvals/{row_id}/decide",
        json={"decision": "approve", "payloadHash": "0" * 64},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "PAYLOAD_HASH_MISMATCH"


def test_approval_withdraw_allows_submitter_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, submitter_id, _ = _pending_approval(api_engine, approval_type="api-withdraw")
    use_principal(_principal(submitter_id, "operator"))
    assert json_client.post(f"/api/v1/approvals/{row_id}/withdraw").status_code == 200
    row2_id, _, _ = _pending_approval(api_engine, approval_type="api-withdraw-denied")
    use_principal(_principal(role="guest"))
    assert json_client.post(f"/api/v1/approvals/{row2_id}/withdraw").status_code == 404
    use_principal(_principal(role="admin"))
    assert json_client.post(f"/api/v1/approvals/{uuid4()}/withdraw").status_code == 404


def test_initiator_confirm_allows_initiator_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, submitter_id, _ = _awaiting_initiator(api_engine)
    use_principal(_principal(submitter_id, "operator"))
    response = json_client.post(
        f"/api/v1/approvals/{row_id}/initiator-confirm", json={"confirm": True}
    )
    assert response.status_code == 200
    assert response.json()["approval"]["initiatorConfirmedBy"] == str(submitter_id)
    assert (
        response.json()["approval"]["initiatorConfirmationHash"]
        == hashlib.sha256(b'{"confirm":true}').hexdigest()
    )

    row2_id, _, _ = _awaiting_initiator(api_engine)
    use_principal(_principal(role="guest"))
    assert (
        json_client.post(f"/api/v1/approvals/{row2_id}/initiator-confirm", json={}).status_code
        == 404
    )
    use_principal(_principal(role="admin"))
    assert (
        json_client.post(f"/api/v1/approvals/{uuid4()}/initiator-confirm", json={}).status_code
        == 404
    )


def test_initiator_confirm_rejects_non_initiator(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, _, _ = _awaiting_initiator(api_engine)
    with Session(api_engine) as session, session.begin():
        other = _user(session, f"other-{uuid4().hex[:8]}", Role.OPERATOR)
        other_id = other.id
    use_principal(_principal(other_id, "operator"))
    assert (
        json_client.post(
            f"/api/v1/approvals/{row_id}/initiator-confirm", json={"confirm": True}
        ).status_code
        == 404
    )


def test_workflow_rule_update_allows_admin_rejects_viewer_and_returns_404(
    json_client: TestClient, api_engine, use_principal
) -> None:
    with Session(api_engine) as session, session.begin():
        row = _rule(session, f"api-rule-{uuid4().hex[:8]}")
        rule_id = row.id
    use_principal(_principal(role="admin"))
    assert (
        json_client.put(f"/api/v1/workflow/rules/{rule_id}", json={"steps": []}).status_code == 200
    )
    with Session(api_engine) as session, session.begin():
        row = _rule(session, f"api-rule-denied-{uuid4().hex[:8]}")
        denied_id = row.id
    use_principal(_principal(role="guest"))
    assert (
        json_client.put(f"/api/v1/workflow/rules/{denied_id}", json={"steps": []}).status_code
        == 404
    )
    use_principal(_principal(role="admin"))
    assert (
        json_client.put(f"/api/v1/workflow/rules/{uuid4()}", json={"steps": []}).status_code == 404
    )


def test_ai_principal_is_rejected_by_all_critical_audit_approval_actions(
    json_client: TestClient, api_engine, use_principal
) -> None:
    row_id, _, approver_id = _pending_approval(api_engine, approval_type="api-ai-decide")
    agent = Principal(
        user_id=approver_id,
        roles=frozenset({"admin"}),
        actor_type=ActorType.AGENT,
        agent_id="critical-agent",
        on_behalf_of=approver_id,
        channel="mcp",
    )
    use_principal(agent)
    for path, method, kwargs in [
        (f"/api/v1/approvals/{row_id}/decide", "post", {"json": {"decision": "approve"}}),
        (f"/api/v1/approvals/{row_id}/withdraw", "post", {}),
        (f"/api/v1/approvals/{row_id}/initiator-confirm", "post", {"json": {"ok": True}}),
        ("/api/v1/audit/retention", "put", {"json": {"retainDays": 30}}),
        ("/api/v1/audit/retention/archive", "post", {}),
    ]:
        assert getattr(json_client, method)(path, **kwargs).status_code in {403, 404}

    with Session(api_engine) as session, session.begin():
        alert = AuditAlert(
            id=uuid4(), kind="agent", status="open", detail_json={}, created_at=datetime.now(UTC)
        )
        session.add(alert)
        alert_id = alert.id
        rule = _rule(session, f"api-ai-rule-{uuid4().hex[:8]}")
        rule_id = rule.id
    assert json_client.post(f"/api/v1/audit/alerts/{alert_id}/resolve").status_code == 403
    assert (
        json_client.put(f"/api/v1/workflow/rules/{rule_id}", json={"steps": []}).status_code == 403
    )


def test_approval_resolution_filter_and_three_reasons(
    api_engine, json_client, use_principal
) -> None:
    with Session(api_engine) as session, session.begin():
        submitter = _user(session, f"resolution-{uuid4().hex[:8]}", Role.OPERATOR, Role.FINANCE)
        self_rule = WorkflowRule(
            id=uuid4(),
            approval_type="api-only-self",
            version=1,
            steps_json=[{"kind": "specific_user", "userId": str(submitter.id)}],
            enabled=True,
            updated_at=datetime.now(UTC),
        )
        session.add(self_rule)
        _rule(session, "api-no-account", role="viewer")
        human = Principal(user_id=submitter.id)
        only_self = ApprovalGatewayImpl(session).submit(
            principal=human,
            entity="mapping",
            action="create",
            payload={"a": 1},
            risk_tier="low",
            approval_type="api-only-self",
        )
        no_account = ApprovalGatewayImpl(session).submit(
            principal=human,
            entity="mapping",
            action="create",
            payload={"a": 2},
            risk_tier="low",
            approval_type="api-no-account",
        )
        no_rule = ApprovalGatewayImpl(session).submit(
            principal=human,
            entity="mapping",
            action="create",
            payload={"a": 3},
            risk_tier="low",
            approval_type="api-no-rule",
        )
        ids = {
            "only_self": str(only_self.id),
            "no_account": str(no_account.id),
            "no_rule": str(no_rule.id),
        }
    use_principal(_principal(role="admin"))
    for reason, expected_id in ids.items():
        response = json_client.get("/api/v1/approvals", params={"q": reason})
        assert response.status_code == 200
        assert expected_id in {item["id"] for item in response.json()["items"]}


def test_admin_submitter_with_approver_rule_stays_pending(api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        admin = _user(session, f"admin-submit-{uuid4().hex[:8]}", Role.ADMIN)
        approver = _user(session, f"admin-approver-{uuid4().hex[:8]}", Role.FINANCE)
        _rule(session, "api-admin-rule")
        row = ApprovalGatewayImpl(session).submit(
            principal=Principal(user_id=admin.id),
            entity="voucher",
            action="post",
            payload={"value": 3},
            risk_tier="high",
            approval_type="api-admin-rule",
        )
        assert row.state == "pending"
        assert str(approver.id) in row.approver_ids


def test_multilevel_rule_with_no_live_steps_is_auto_effective(api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        submitter = _user(session, f"all-skip-{uuid4().hex[:8]}", Role.OPERATOR)
        row_rule = WorkflowRule(
            id=uuid4(),
            approval_type="api-all-skip",
            version=1,
            steps_json=[
                {"kind": "specific_user", "userId": str(uuid4())},
                {"kind": "specific_user", "userId": str(uuid4())},
            ],
            enabled=True,
            updated_at=datetime.now(UTC),
        )
        session.add(row_rule)
        row = ApprovalGatewayImpl(session).submit(
            principal=Principal(user_id=submitter.id),
            entity="mapping",
            action="create",
            payload={"value": 4},
            risk_tier="low",
            approval_type="api-all-skip",
        )
        assert row.state == "auto_effective"
        assert row.resolution["reason"] == "no_account"
        assert all(step["skipped"] for step in row.resolution["snapshot"])


def test_agent_audit_context_and_chain_tamper_detection(
    json_client: TestClient, api_engine, use_principal
) -> None:
    represented = uuid4()
    with Session(api_engine) as session, session.begin():
        row = _audit_row(
            session,
            actor_type="agent",
            actor_user_id=uuid4(),
            agent_id="agent-context",
            on_behalf_of=represented,
            delegation_id="delegation-context",
            run_id="run-context",
            tool_call_id="tool-context",
            is_subagent=True,
            channel="mcp",
            request_id="request-context",
        )
        row_id = row.id
    use_principal(_principal(role="admin"))
    item = json_client.get(f"/api/v1/audit/logs/{row_id}").json()
    assert item["actorType"] == "agent"
    assert item["agentId"] == "agent-context"
    assert item["onBehalfOf"] == str(represented)
    assert item["channel"] == "mcp"
    assert item["requestId"] == "request-context"
    with Session(api_engine) as session, session.begin():
        row = session.get(AuditLog, row_id)
        assert row is not None
        row.delegation_id = "tampered"
    with Session(api_engine) as session:
        assert verify_chain(session).ok is False
    assert json_client.get("/api/v1/audit/chain").json()["ok"] is False


def test_ledger_write_service_accepts_only_effective_approval_states(
    tmp_path: Path,
) -> None:
    from crosserp.approval.service import hash_token
    from tests.guard.test_denials import _report

    database_url = sqlite_file_url(tmp_path / "ledger.db")
    upgrade_head(database_url)
    engine = make_engine(database_url)
    with Session(engine) as session, session.begin():
        batch, payload_hash = _report(session, store_name="api-ledger")
    accepted = ("approved", "auto_effective", "initiator_confirmed")
    rejected = ("pending", "awaiting_initiator", "rejected")
    for index, state in enumerate((*accepted, *rejected)):
        token = f"api-token-{index}"
        with Session(engine) as session, session.begin():
            row = Approval(
                id=uuid4(),
                target_type="profit_report",
                target_id="api-ledger:2026-10",
                state=state,
                payload_hash=payload_hash,
                content_hash=payload_hash,
                requested_by="operator",
                requested_at=datetime.now(UTC),
                approval_type="voucher",
                risk_tier="high",
                actor_type="human",
                resolution={"mode": state},
                approver_ids=[],
                current_step=0,
                token_hash=hash_token(token),
            )
            session.add(row)
        with Session(engine) as session:
            if state in accepted:
                artifact = export(session, batch, "xlsx", token, output_dir=tmp_path)
                assert artifact.file_path
            else:
                with pytest.raises(ApprovalRequired):
                    export(session, batch, "xlsx", token, output_dir=tmp_path)
    engine.dispose()
    downgrade_base(database_url)
