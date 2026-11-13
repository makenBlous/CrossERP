from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AppSetting, AppUser, IamDataScopeRule
from crosserp.iam.service import IAMService
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import ActorType, Principal


@pytest.fixture
def iam_service(engine):
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        yield IAMService(engine)
    finally:
        downgrade_base(url)


def _add_user(engine, user_id) -> None:
    with Session(engine) as session, session.begin():
        session.add(
            AppUser(
                id=user_id,
                username=f"iam-{user_id.hex[:12]}",
                display_name="IAM",
                password_hash="x",
                is_active=True,
                failed_logins=0,
                password_changed_at=datetime.now(UTC),
                must_change_password=False,
                created_at=datetime.now(UTC),
                permission_version=0,
            )
        )


def test_store_scope_uses_iam_store_rules(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    allowed = uuid4()
    other = uuid4()
    _add_user(engine, user_id)
    with Session(engine) as session, session.begin():
        session.add(
            IamDataScopeRule(
                name="sku-stores",
                entity="Sku",
                scope_type="storeIds",
                values=[str(allowed)],
                updated_by=user_id,
                updated_at=datetime.now(UTC),
            )
        )
    service = DefaultPermissionService(iam_service)
    principal = Principal(user_id=user_id)
    scope = service.store_scope(principal, "Sku")
    assert allowed in scope
    assert other not in scope


def test_data_scope_rules_do_not_read_app_settings(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    _add_user(engine, user_id)
    with Session(engine) as session, session.begin():
        session.add(
            AppSetting(
                key=f"data_scope:{user_id}",
                value_json={"storeIds": ["from-app-setting"]},
                updated_by=user_id,
                updated_at=datetime.now(UTC),
            )
        )

    scope = iam_service.data_scope_filter(Principal(user_id=user_id), "Store")

    assert scope == {"entity": "Store", "scopes": [], "filters": {}}


def test_denial_wins_over_role_and_user_grant(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    _add_user(engine, user_id)
    iam_service.create_role(
        "base", name="base", permissions={"report:read"}, parent_ids=set(), data_scopes=set()
    )
    iam_service.assign_role(user_id, "base")
    iam_service.set_override(user_id, "report:read", effect="deny", reason="sod")
    assert iam_service.effective_permission(user_id, "report:read").allowed is False


def test_expired_temporary_grant_is_not_effective(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    _add_user(engine, user_id)
    iam_service.set_temporary_grant(
        user_id,
        "report:read",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert iam_service.effective_permission(user_id, "report:read").allowed is False


def test_inheritance_cycle_is_rejected(iam_service: IAMService) -> None:
    iam_service.create_role("a", name="a", permissions=set(), parent_ids=set(), data_scopes=set())
    iam_service.create_role("b", name="b", permissions=set(), parent_ids={"a"}, data_scopes=set())
    with pytest.raises(APIError, match="循环"):
        iam_service.update_role("a", parent_ids={"b"})


def test_ai_can_only_narrow_and_cannot_execute_critical(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    _add_user(engine, user_id)
    iam_service.create_role(
        "base",
        name="base",
        permissions={"report:read", "permission:write"},
        parent_ids=set(),
        data_scopes=set(),
    )
    iam_service.assign_role(user_id, "base")
    human = Principal(user_id=user_id)
    agent = Principal(
        user_id=user_id,
        on_behalf_of=user_id,
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
    )
    iam_service.require(human, "report:read")
    iam_service.require(agent, "report:read", allowed_permissions={"report:read"})
    with pytest.raises(APIError):
        iam_service.require(
            agent,
            "permission:write",
            allowed_permissions={"permission:write"},
            risk_tier="critical",
        )


def test_permission_version_increments_on_effective_change(iam_service: IAMService, engine) -> None:
    user_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            AppUser(
                id=user_id,
                username="iam-version",
                display_name="IAM version",
                password_hash="x",
                is_active=True,
                failed_logins=0,
                password_changed_at=datetime.now(UTC),
                must_change_password=False,
                created_at=datetime.now(UTC),
                permission_version=0,
            )
        )
    assert iam_service.permission_version(user_id) == 0
    iam_service.set_override(user_id, "report:read", effect="allow", reason="temporary")
    assert iam_service.permission_version(user_id) == 1


def test_field_serializer_removes_denied_fields(iam_service: IAMService) -> None:
    user_id = uuid4()
    record = {"id": "1", "salary": 100, "name": "A"}
    assert iam_service.serialize(user_id, record, {"salary": "salary:read"}) == {
        "id": "1",
        "name": "A",
    }
