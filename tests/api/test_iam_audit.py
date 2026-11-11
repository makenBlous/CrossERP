from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.security import verify_security_chain
from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, SecurityEvent
from crosserp.platform.principal import ActorType, Principal, get_principal


def test_iam_write_audit_has_actor_context_and_ai_critical_is_rejected(
    json_client, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        human_user = create_user(
            session,
            username="iam-audit-admin",
            password="Iam-audit-password-123",
            roles=(Role.ADMIN,),
        )
        human_user_id = human_user.id
    human = Principal(user_id=human_user_id, roles=frozenset({"admin"}))
    json_client.app.dependency_overrides[get_principal] = lambda: human
    try:
        response = json_client.post(
            "/api/v1/admin/roles", json={"slug": "audit-route", "permissions": ["report:read"]}
        )
        assert response.status_code == 201, response.text
        agent = Principal(
            user_id=human.user_id,
            roles=human.roles,
            actor_type=ActorType.AGENT,
            agent_id="audit-agent",
            on_behalf_of=human.user_id,
        )
        json_client.app.dependency_overrides[get_principal] = lambda: agent
        denied = json_client.post(
            "/api/v1/admin/roles", json={"slug": "agent-route", "permissions": ["report:read"]}
        )
        assert denied.status_code == 403
    finally:
        json_client.app.dependency_overrides.pop(get_principal, None)
    with Session(api_engine) as session:
        row = session.scalar(
            select(AuditLog).where(AuditLog.action == "Role.create").order_by(AuditLog.seq.desc())
        )
        assert row is not None
        assert row.actor_type == "human"
        assert row.after_json["agent_id"] is None
        assert row.after_json["on_behalf_of"] is None
        assert (
            session.scalar(select(SecurityEvent).where(SecurityEvent.event == "permission_changed"))
            is not None
        )
        assert verify_security_chain(session)
