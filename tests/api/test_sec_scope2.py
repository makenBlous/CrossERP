"""角色数据范围: 并集、用户例外、本人负责店铺和 AI 收窄。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AgentStoreScope,
    IamDataScopeRule,
    IamPermissionOverride,
    IamRole,
    Sku,
    Store,
    UserRole,
    UserStoreGrant,
)
from crosserp.demo.scopes import seed_demo_role_accounts
from crosserp.iam.catalog import load_role_template_scopes
from crosserp.iam.scope import AllLegalEntities, AllPeriods
from crosserp.iam.service import IAMService
from crosserp.platform.principal import ActorType, Principal, get_principal


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def _store(name: str) -> Store:
    return Store(id=uuid4(), platform="amazon", marketplace="US", name=name, currency="USD")


def _sku(store_id: UUID, internal_sku: str) -> Sku:
    now = datetime.now(UTC)
    return Sku(
        id=uuid4(),
        store_id=store_id,
        platform_sku=internal_sku,
        internal_sku=internal_sku,
        title=internal_sku,
        aliases_json=[],
        active=True,
        created_at=now,
        updated_at=now,
    )


def _grant(user_id: UUID, store_id: UUID, granted_by: UUID) -> UserStoreGrant:
    return UserStoreGrant(
        user_id=user_id,
        store_id=store_id,
        granted_by=granted_by,
        granted_at=datetime.now(UTC),
    )


def _role(session: Session, user_id: UUID, role_id: str) -> None:
    session.add(UserRole(user_id=user_id, role=role_id, granted_at=datetime.now(UTC)))


def test_template_scopes_follow_design_and_are_not_all_all(api_engine) -> None:
    scopes = load_role_template_scopes()
    assert scopes["store_operator"] == ["ownedStores"]
    assert scopes["advertising"] == ["ownedStores"]
    assert scopes["customer_service"] == ["ownedStores"]
    assert scopes["owner_manager"] == ["all"]
    assert scopes["operations_manager"] == ["department"]
    assert scopes["auditor_template"] == ["all"]
    assert scopes["finance_manager"] == ["all"]
    assert any(value != ["all"] for value in scopes.values())
    with Session(api_engine) as session:
        rows = {
            row.slug: list(row.data_scopes)
            for row in session.scalars(select(IamRole).where(IamRole.is_template.is_(True)))
        }
    assert rows["store_operator"] == ["ownedStores"]
    assert rows["owner_manager"] == ["all"]
    assert rows["warehouse_logistics"] == ["warehouse"]
    assert any(value != ["all"] for value in rows.values())


def test_different_roles_see_different_owned_stores(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        operator = create_user(session, username="op-owned", password="Scope-test-password-123")
        ads = create_user(session, username="ads-owned", password="Scope-test-password-123")
        first = _store("owned-a")
        second = _store("owned-b")
        session.add_all([first, second])
        session.flush()
        _role(session, operator.id, "store_operator")
        _role(session, ads.id, "advertising")
        session.add_all(
            [
                _grant(operator.id, first.id, operator.id),
                _grant(ads.id, second.id, ads.id),
            ]
        )
    _login(json_client, "op-owned", "Scope-test-password-123")
    operator_names = [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]]
    _login(json_client, "ads-owned", "Scope-test-password-123")
    ads_names = [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]]

    assert operator_names == ["owned-a"]
    assert ads_names == ["owned-b"]


def test_multiple_roles_union_store_rules(json_client: TestClient, api_engine) -> None:
    iam = IAMService(api_engine)
    iam.create_role(
        "scope-east", name="东区", permissions={"report:read"}, parent_ids=set(), data_scopes=set()
    )
    iam.create_role(
        "scope-west",
        name="西区",
        permissions={"report:read"},
        parent_ids={"scope-east"},
        data_scopes=set(),
    )
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="union-user", password="Scope-test-password-123")
        east = _store("east")
        west = _store("west")
        session.add_all([east, west])
        session.flush()
        east_role = session.scalar(select(IamRole).where(IamRole.slug == "scope-east"))
        west_role = session.scalar(select(IamRole).where(IamRole.slug == "scope-west"))
        assert east_role is not None and west_role is not None
        now = datetime.now(UTC)
        session.add_all(
            [
                IamDataScopeRule(
                    name="east-stores",
                    entity="*",
                    scope_type="storeIds",
                    values=[str(east.id)],
                    role_id=east_role.id,
                    updated_at=now,
                ),
                IamDataScopeRule(
                    name="west-stores",
                    entity="*",
                    scope_type="storeIds",
                    values=[str(west.id)],
                    role_id=west_role.id,
                    updated_at=now,
                ),
            ]
        )
        _role(session, user.id, "scope-west")
    _login(json_client, "union-user", "Scope-test-password-123")
    names = [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]]

    assert names == ["east", "west"]


def test_user_exception_adds_store_outside_owned_scope(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="exception-user", password="Scope-test-password-123")
        owned = _store("exception-owned")
        extra = _store("exception-extra")
        session.add_all([owned, extra])
        session.flush()
        _role(session, user.id, "store_operator")
        session.add(_grant(user.id, owned.id, user.id))
        session.add(
            IamPermissionOverride(
                user_id=user.id,
                permission="report:read",
                effect="allow",
                reason="临时看另一店",
                data_scopes=[f"store:{extra.id}"],
                created_at=datetime.now(UTC),
            )
        )
    _login(json_client, "exception-user", "Scope-test-password-123")
    names = [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]]

    assert names == ["exception-extra", "exception-owned"]


def test_agent_narrowing_cannot_expand_owned_stores(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="agent-narrow", password="Scope-test-password-123")
        owned = _store("agent-owned")
        foreign = _store("agent-foreign")
        session.add_all([owned, foreign])
        session.flush()
        session.add(_sku(owned.id, "SKU-AGENT-OWNED"))
        session.add(_sku(foreign.id, "SKU-AGENT-FOREIGN"))
        _role(session, user.id, "store_operator")
        session.add(_grant(user.id, owned.id, user.id))
        session.add(AgentStoreScope(agent_id="narrow-agent", store_id=owned.id))
        session.add(AgentStoreScope(agent_id="narrow-agent", store_id=foreign.id))
        user_id = user.id
    json_client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user_id,
        roles=frozenset({"store_operator"}),
        actor_type=ActorType.AGENT,
        agent_id="narrow-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    try:
        response = json_client.get("/api/v1/catalog/skus")
    finally:
        json_client.app.dependency_overrides.pop(get_principal, None)

    assert response.status_code == 200
    assert [item["internalSku"] for item in response.json()["items"]] == ["SKU-AGENT-OWNED"]


def test_agent_narrowing_reduces_owner_all_to_one_store(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="agent-owner", password="Scope-test-password-123")
        visible = _store("agent-visible")
        hidden = _store("agent-hidden")
        session.add_all([visible, hidden])
        session.flush()
        session.add(_sku(visible.id, "SKU-NARROW-YES"))
        session.add(_sku(hidden.id, "SKU-NARROW-NO"))
        _role(session, user.id, "owner_manager")
        session.add(AgentStoreScope(agent_id="owner-agent", store_id=visible.id))
        user_id = user.id
    json_client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user_id,
        roles=frozenset({"owner_manager"}),
        actor_type=ActorType.AGENT,
        agent_id="owner-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    try:
        response = json_client.get("/api/v1/catalog/skus")
    finally:
        json_client.app.dependency_overrides.pop(get_principal, None)

    assert response.status_code == 200
    assert [item["internalSku"] for item in response.json()["items"]] == ["SKU-NARROW-YES"]


def test_store_operator_without_grants_sees_nothing(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="op-empty", password="Scope-test-password-123")
        hidden = _store("not-owned")
        session.add(hidden)
        session.flush()
        session.add(_sku(hidden.id, "SKU-NOT-OWNED"))
        _role(session, user.id, "store_operator")
        hidden_store_id = hidden.id
        hidden_sku_id = session.scalar(select(Sku.id).where(Sku.internal_sku == "SKU-NOT-OWNED"))
    _login(json_client, "op-empty", "Scope-test-password-123")

    listed = json_client.get("/api/v1/stores")
    detail = json_client.get(f"/api/v1/catalog/skus/{hidden_sku_id}")
    created = json_client.post(
        "/api/v1/catalog/skus",
        json={
            "internalSku": "SKU-DENIED",
            "platformSku": "SKU-DENIED",
            "title": "越权",
            "storeId": str(hidden_store_id),
        },
    )

    assert listed.status_code == 200
    assert listed.json()["items"] == []
    assert detail.status_code == 404
    assert detail.json()["code"] == "NOT_FOUND"
    assert created.status_code == 403
    assert created.json()["code"] == "DATA_SCOPE_DENIED"


def test_store_tokens_do_not_invalidate_period_or_legal_scope(api_engine) -> None:
    iam = IAMService(api_engine)
    with Session(api_engine) as session, session.begin():
        operator = create_user(
            session, username="period-operator", password="Scope-test-password-123"
        )
        owner = create_user(session, username="period-owner", password="Scope-test-password-123")
        _role(session, operator.id, "store_operator")
        _role(session, owner.id, "owner_manager")
        operator_id = operator.id
        owner_id = owner.id
        role = session.scalar(select(IamRole).where(IamRole.slug == "store_operator"))
        assert role is not None
        session.add(
            IamDataScopeRule(
                name="operator-periods",
                entity="ReconRun",
                scope_type="periods",
                values=["2026-10"],
                role_id=role.id,
                updated_at=datetime.now(UTC),
            )
        )
    operator_principal = Principal(user_id=operator_id, roles=frozenset({"store_operator"}))
    owner_principal = Principal(user_id=owner_id, roles=frozenset({"owner_manager"}))

    assert iam.period_scope(operator_principal, "ReconRun") == frozenset({"2026-10"})
    assert iam.legal_entity_scope(operator_principal, "ExportPackage") == frozenset()
    assert isinstance(iam.period_scope(owner_principal, "ReconRun"), AllPeriods)
    assert isinstance(iam.legal_entity_scope(owner_principal, "ExportPackage"), AllLegalEntities)
    with Session(api_engine) as session, session.begin():
        session.add(
            IamDataScopeRule(
                name="bad-periods",
                entity="ReconRun",
                scope_type="periods",
                values=["not-a-period"],
                role_id=session.scalar(select(IamRole.id).where(IamRole.slug == "store_operator")),
                updated_at=datetime.now(UTC),
            )
        )
    try:
        iam.period_scope(operator_principal, "ReconRun")
    except APIError as exc:
        assert exc.code.value == "VALIDATION_FAILED"
    else:
        raise AssertionError("畸形期间规则必须失败关闭")


def test_owner_manager_sees_all_stores(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username="boss-all", password="Scope-test-password-123")
        session.add_all([_store("boss-a"), _store("boss-b")])
        _role(session, user.id, "owner_manager")
    _login(json_client, "boss-all", "Scope-test-password-123")
    names = [item["name"] for item in json_client.get("/api/v1/stores").json()["items"]]

    assert names == ["boss-a", "boss-b"]


def test_demo_seed_assigns_owned_stores_by_role(api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        admin = create_user(session, username="demo-granter", password="Scope-test-password-123")
        session.add_all([_store("Amazon.de"), _store("Amazon.com")])
        session.flush()
        created = seed_demo_role_accounts(session, granted_by=admin.id)
        rows = session.execute(
            select(Store.name, UserRole.role)
            .join(UserStoreGrant, UserStoreGrant.store_id == Store.id)
            .join(UserRole, UserRole.user_id == UserStoreGrant.user_id)
        ).all()
    created_names = {username for username, _password in created}
    grants = {(role, name) for name, role in rows}

    assert "demo-store-operator" in created_names
    assert ("store_operator", "Amazon.com") in grants
    assert ("advertising", "Amazon.de") in grants
