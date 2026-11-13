"""确认费用分类 MappingRule.confirm。"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import (
    Approval,
    AuditLog,
    IamDataScopeRule,
    MappingRule,
    Store,
    UserRole,
    WorkflowRule,
)
from crosserp.platform.principal import ActorType, Principal


def _principal(*permissions: str, agent: bool = False) -> Principal:
    user_id = uuid4()
    return Principal(
        user_id=user_id,
        permissions=frozenset(permissions),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="fee-agent" if agent else None,
        on_behalf_of=user_id if agent else None,
        channel="mcp" if agent else "web",
        run_id="fee-run" if agent else None,
    )


def _override(client: TestClient, principal: Principal, role: str | None) -> Principal:
    from crosserp.platform.principal import get_principal

    with Session(client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"feemap-{uuid4().hex}",
            password="Feemap-test-password-123",
        )
        if role is not None:
            grant_role(session, user.id, role)
        user_id = user.id
    effective = replace(
        principal, user_id=user_id, on_behalf_of=user_id if principal.is_agent else None
    )
    client.app.dependency_overrides[get_principal] = lambda: effective
    return effective


def _rule(
    engine,
    *,
    kind: str = "fee",
    version: int = 1,
    verified: bool = False,
    store_id: UUID | None = None,
    rule_key: str = "amazon-fee",
) -> str:
    now = datetime.now(UTC)
    rule_id = uuid4()
    body: dict[str, str] = {
        "amountType": "ItemFees",
        "amountDescription": "Commission",
        "feeCategory": "commission",
    }
    if store_id is not None:
        body["storeId"] = str(store_id)
    with Session(engine) as session, session.begin():
        session.add(
            MappingRule(
                id=rule_id,
                rule_key=rule_key,
                rule_version="v1",
                kind=kind,
                body_json=body,
                status="active",
                verified=verified,
                version=version,
                created_at=now,
                updated_at=now,
            )
        )
    return str(rule_id)


def _confirm(
    client: TestClient,
    rule_id: str,
    *,
    key: str | None = None,
    expected_version: int | None = 1,
    comment: str | None = None,
) -> object:
    body: dict[str, object] = {}
    if expected_version is not None:
        body["expectedVersion"] = expected_version
    if comment is not None:
        body["comment"] = comment
    headers = {"X-Request-ID": "fee-confirm-req"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(f"/api/v1/finance/fee-map/{rule_id}/confirm", json=body, headers=headers)


def test_confirm_requires_login(json_client: TestClient) -> None:
    response = json_client.post(
        f"/api/v1/finance/fee-map/{uuid4()}/confirm",
        json={"expectedVersion": 1},
        headers={"Idempotency-Key": "fee-anon"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_confirm_hides_missing_unauthorized_and_non_fee(
    json_client: TestClient, api_engine
) -> None:
    _override(json_client, _principal(), None)
    denied = json_client.post(
        f"/api/v1/finance/fee-map/{uuid4()}/confirm",
        json={"expectedVersion": 1},
        headers={"Idempotency-Key": "fee-denied"},
    )
    assert denied.status_code == 404

    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    missing = _confirm(json_client, str(uuid4()), key="fee-missing")
    assert missing.status_code == 404
    column_id = _rule(api_engine, kind="column")
    column = _confirm(json_client, column_id, key="fee-column")
    assert column.status_code == 404
    assert principal.user_id is not None


def test_human_confirm_commits_replays_and_is_audited(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    rule_id = _rule(api_engine)
    first = _confirm(json_client, rule_id, key="fee-ok")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["state"] == "auto_effective"
    assert body["applied"] is True
    assert body["verified"] is True
    assert body["id"] == rule_id

    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(rule_id))
        assert row is not None
        assert row.verified is True
        assert row.version == 2
        audit = fresh.scalar(
            select(AuditLog)
            .where(AuditLog.action == "MappingRule.confirm")
            .order_by(AuditLog.seq.desc())
        )
        assert audit is not None
        assert audit.actor_type == "human"
        assert audit.on_behalf_of is None
        assert audit.request_id == "fee-confirm-req"
        assert audit.actor_user_id == principal.user_id

    replay = _confirm(json_client, rule_id, key="fee-ok")
    assert replay.status_code == 200
    assert replay.json() == body
    with Session(api_engine) as fresh:
        assert fresh.scalar(select(MappingRule).where(MappingRule.verified.is_(True))).version == 2


def test_human_with_approver_does_not_confirm_and_cannot_self_approve(
    json_client: TestClient, api_engine
) -> None:
    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        approver = create_user(
            session,
            username=f"fee-approver-{uuid4().hex[:8]}",
            password="Feemap-test-password-123",
            roles=(Role.FINANCE,),
        )
        session.add(
            WorkflowRule(
                id=uuid4(),
                approval_type="mappingrule",
                version=1,
                steps_json=[
                    {"kind": "specific_user", "userId": str(principal.user_id)},
                    {"kind": "specific_user", "userId": str(approver.id)},
                ],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
        )
        approver_id = approver.id
    rule_id = _rule(api_engine)
    response = _confirm(json_client, rule_id, key="fee-pending")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "pending"
    assert response.json()["applied"] is False
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(rule_id))
        approval = fresh.scalar(select(Approval).where(Approval.target_id == "MappingRule.confirm"))
        assert row is not None and row.verified is False and row.version == 1
        assert approval is not None
        assert approval.state == "pending"
        assert str(principal.user_id) not in approval.approver_ids
        assert str(approver_id) in approval.approver_ids
        assert approval.approver is None


def test_only_self_approver_auto_effects_without_self_approval(
    json_client: TestClient, api_engine
) -> None:
    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        session.add(
            WorkflowRule(
                id=uuid4(),
                approval_type="mappingrule",
                version=1,
                steps_json=[{"kind": "specific_user", "userId": str(principal.user_id)}],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
        )
    rule_id = _rule(api_engine)
    response = _confirm(json_client, rule_id, key="fee-only-self")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "auto_effective"
    assert response.json()["resolution"]["reason"] == "only_self"
    with Session(api_engine) as fresh:
        approval = fresh.scalar(select(Approval).where(Approval.target_id == "MappingRule.confirm"))
        row = fresh.get(MappingRule, UUID(rule_id))
        assert approval is not None
        assert str(principal.user_id) not in (approval.approver_ids or [])
        assert approval.approver is None
        assert row is not None and row.verified is True


def test_agent_confirm_waits_without_marking_verified(json_client: TestClient, api_engine) -> None:
    principal = _override(
        json_client, _principal("integration:write", agent=True), Role.ADMIN.value
    )
    rule_id = _rule(api_engine)
    response = _confirm(json_client, rule_id, key="fee-agent")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "awaiting_initiator"
    assert body.get("verified") is not True
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(rule_id))
        audit = fresh.scalar(
            select(AuditLog)
            .where(AuditLog.action == "MappingRule.confirm")
            .order_by(AuditLog.seq.desc())
        )
        assert row is not None and row.verified is False and row.version == 1
        assert audit is not None
        assert audit.actor_type == "agent"
        assert audit.agent_id == "fee-agent"
        assert audit.on_behalf_of == str(principal.on_behalf_of)
        assert audit.request_id == "fee-confirm-req"
        assert audit.run_id == "fee-run"
    replay = _confirm(json_client, rule_id, key="fee-agent")
    assert replay.status_code == 200
    assert replay.json() == body


def test_agent_with_approver_stays_pending(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal("integration:write", agent=True), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        approver = create_user(
            session,
            username=f"fee-agent-approver-{uuid4().hex[:8]}",
            password="Feemap-test-password-123",
            roles=(Role.FINANCE,),
        )
        session.add(
            WorkflowRule(
                id=uuid4(),
                approval_type="mappingrule",
                version=1,
                steps_json=[{"kind": "specific_user", "userId": str(approver.id)}],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
        )
    rule_id = _rule(api_engine)
    response = _confirm(json_client, rule_id, key="fee-agent-pending")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "pending"
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(rule_id))
        assert row is not None and row.verified is False


def test_expected_version_conflict_does_not_overwrite(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    rule_id = _rule(api_engine, version=3)
    conflict = _confirm(json_client, rule_id, key="fee-stale", expected_version=1)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(rule_id))
        assert row is not None and row.verified is False and row.version == 3
        assert (
            fresh.scalar(select(Approval).where(Approval.target_id == "MappingRule.confirm"))
            is None
        )


def test_same_key_different_body_conflicts(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    rule_id = _rule(api_engine)
    first = _confirm(json_client, rule_id, key="fee-body", comment="第一次")
    assert first.status_code == 200
    conflict = _confirm(json_client, rule_id, key="fee-body", comment="第二次")
    assert conflict.status_code == 409
    assert conflict.json()["code"] in {"IDEMPOTENCY_CONFLICT", "IDEMPOTENCY_REPLAY_MISMATCH"}


def test_other_user_same_key_is_not_found(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    rule_id = _rule(api_engine)
    first = _confirm(json_client, rule_id, key="fee-hidden-key")
    assert first.status_code == 200
    _override(json_client, _principal(), None)
    hidden = _confirm(json_client, rule_id, key="fee-hidden-key")
    assert hidden.status_code == 404
    assert hidden.json() != first.json()


def test_revoked_permission_replay_is_not_found(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    rule_id = _rule(api_engine)
    first = _confirm(json_client, rule_id, key="fee-revoke")
    assert first.status_code == 200
    with Session(api_engine) as session, session.begin():
        session.execute(delete(UserRole).where(UserRole.user_id == principal.user_id))
    replay = _confirm(json_client, rule_id, key="fee-revoke")
    assert replay.status_code == 404


def test_out_of_scope_write_is_denied_and_in_scope_store_confirms(
    json_client: TestClient, api_engine
) -> None:
    principal = _override(json_client, _principal("integration:write"), Role.ADMIN.value)
    visible = uuid4()
    hidden = uuid4()
    with Session(api_engine) as session, session.begin():
        session.add_all(
            [
                Store(
                    id=visible, platform="amazon", marketplace="US", name="可见店", currency="USD"
                ),
                Store(
                    id=hidden, platform="amazon", marketplace="US", name="范围外店", currency="USD"
                ),
                IamDataScopeRule(
                    name="feemap-stores",
                    entity="MappingRule",
                    scope_type="storeIds",
                    values=[str(visible)],
                    updated_by=principal.user_id,
                    updated_at=datetime.now(UTC),
                ),
            ]
        )
    hidden_id = _rule(api_engine, store_id=hidden)
    denied = _confirm(json_client, hidden_id, key="fee-hidden-store")
    assert denied.status_code == 403
    assert denied.json()["code"] == "DATA_SCOPE_DENIED"
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(hidden_id))
        assert row is not None and row.verified is False

    visible_id = _rule(api_engine, store_id=visible, rule_key="amazon-fee-visible")
    allowed = _confirm(json_client, visible_id, key="fee-visible-store")
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["applied"] is True
    with Session(api_engine) as fresh:
        row = fresh.get(MappingRule, UUID(visible_id))
        assert row is not None and row.verified is True
