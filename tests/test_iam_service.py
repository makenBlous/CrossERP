from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from crosserp.iam.service import IAMService
from crosserp.platform.principal import ActorType, Principal


def test_denial_wins_over_role_and_user_grant() -> None:
    service = IAMService()
    user_id = uuid4()
    service.create_role("base", permissions={"report:read"})
    service.assign_role(user_id, "base")
    service.set_override(user_id, "report:read", effect="deny", reason="sod")
    assert service.effective_permission(user_id, "report:read").allowed is False


def test_expired_temporary_grant_is_not_effective() -> None:
    service = IAMService()
    user_id = uuid4()
    service.set_temporary_grant(
        user_id,
        "report:read",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert service.effective_permission(user_id, "report:read").allowed is False


def test_inheritance_cycle_is_rejected() -> None:
    service = IAMService()
    service.create_role("a")
    service.create_role("b", parent_ids={"a"})
    with pytest.raises(ValueError, match="循环"):
        service.update_role("a", parent_ids={"b"})


def test_ai_can_only_narrow_and_cannot_execute_critical() -> None:
    service = IAMService()
    user_id = uuid4()
    service.create_role("base", permissions={"report:read", "permission:write"})
    service.assign_role(user_id, "base")
    human = Principal(user_id=user_id)
    agent = Principal(
        user_id=user_id,
        on_behalf_of=user_id,
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
    )
    service.require(human, "report:read")
    service.require(agent, "report:read", allowed_permissions={"report:read"})
    with pytest.raises(PermissionError):
        service.require(agent, "permission:write", allowed_permissions={"permission:write"})


def test_permission_version_increments_on_effective_change() -> None:
    service = IAMService()
    user_id = uuid4()
    assert service.permission_version(user_id) == 0
    service.set_override(user_id, "report:read", effect="allow", reason="temporary")
    assert service.permission_version(user_id) == 1


def test_field_serializer_removes_denied_fields() -> None:
    service = IAMService()
    user_id = uuid4()
    record = {"id": "1", "salary": 100, "name": "A"}
    assert service.serialize(user_id, record, {"salary": "salary:read"}) == {
        "id": "1",
        "name": "A",
    }
