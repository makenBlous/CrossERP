from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import Approval, AppUser, ImportBatch, MappingRule, WorkflowRule
from crosserp.platform.principal import ActorType, Principal, get_principal


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "password-123"}
    )
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _rule(
    api_engine, *, username: str = "ing-rules", roles: tuple[Role, ...] = (Role.ADMIN,)
) -> tuple[str, str]:
    now = datetime.now(UTC)
    with Session(api_engine) as session, session.begin():
        user = create_user(session, username=username, password="password-123", roles=roles)
        rule = MappingRule(
            id=uuid4(),
            rule_key="orders",
            rule_version="v1",
            kind="column",
            body_json={"columns": {"orderId": "Order ID"}},
            status="active",
            verified=True,
            version=1,
            created_at=now,
        )
        batch = ImportBatch(
            id=uuid4(),
            connector_id="orders",
            connector_version="v1",
            file_name="orders.csv",
            file_sha256="a" * 64,
            imported_at=now,
            row_count=1,
            status="landed",
            error_count=0,
            mapping_rule_version="v1",
            kind="order",
            created_by=user.id,
            received_at=now,
        )
        session.add_all([rule, batch])
        session.flush()
        return str(rule.id), str(batch.id)


def test_put_mapping_rule_creates_new_version_and_preserves_batch_binding(
    json_client: TestClient, api_engine
) -> None:
    rule_id, batch_id = _rule(api_engine)
    csrf = _login(json_client, "ing-rules")

    response = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "ing-rule-update-1"},
        json={"expectedVersion": 1, "body": {"columns": {"orderId": "订单号"}}},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["ruleVersion"] == "v2"
    assert result["status"] == "active"
    assert result["previousId"] == rule_id
    with Session(api_engine) as session:
        old = session.get(MappingRule, UUID(rule_id))
        batch = session.get(ImportBatch, UUID(batch_id))
        assert old is not None and old.status == "superseded"
        assert batch is not None and batch.mapping_rule_version == "v1"
    assert json_client.get("/api/v1/finance/column-maps").status_code == 200
    detail = json_client.get(f"/api/v1/finance/column-maps/{result['id']}")
    assert detail.status_code == 200
    assert detail.json()["ruleVersion"] == "v2"


def test_put_mapping_rule_replays_idempotently_and_rejects_stale_version(
    json_client: TestClient, api_engine
) -> None:
    rule_id, _ = _rule(api_engine, username="ing-rules-idem")
    csrf = _login(json_client, "ing-rules-idem")
    request = {
        "expectedVersion": 1,
        "body": {"columns": {"orderId": "订单号"}},
    }
    first = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "ing-rule-idem"},
        json=request,
    )
    replay = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "ing-rule-idem"},
        json=request,
    )
    stale = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "body": {"columns": {"orderId": "旧值"}}},
    )

    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert stale.status_code == 409


def test_put_mapping_rule_hides_missing_and_unauthorized_resources(
    json_client: TestClient, api_engine
) -> None:
    rule_id, _ = _rule(api_engine, username="ing-rules-viewer", roles=())
    csrf = _login(json_client, "ing-rules-viewer")
    unauthorized = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "body": {}},
    )
    missing = json_client.put(
        f"/api/v1/ingest/mapping-rules/{uuid4()}",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "body": {}},
    )
    assert unauthorized.status_code == 404
    assert missing.status_code == 404


def test_agent_put_mapping_rule_enters_approval_without_changing_active_rule(
    json_client: TestClient, api_engine
) -> None:
    rule_id, _ = _rule(api_engine, username="ing-rules-agent")
    with Session(api_engine) as session, session.begin():
        user = session.scalar(select(AppUser).where(AppUser.username == "ing-rules-agent"))
        assert user is not None
        approver = create_user(
            session, username="ing-rules-approver", password="password-123", roles=(Role.FINANCE,)
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
        agent = Principal(
            user_id=user.id,
            roles=frozenset({Role.ADMIN.value}),
            actor_type=ActorType.AGENT,
            agent_id="mapping-agent",
            on_behalf_of=user.id,
            channel="mcp",
        )
    json_client.app.dependency_overrides[get_principal] = lambda: agent
    response = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        json={"expectedVersion": 1, "body": {"columns": {"orderId": "订单号"}}},
    )
    json_client.app.dependency_overrides.pop(get_principal, None)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    with Session(api_engine) as session:
        approval = session.scalar(
            select(Approval).where(Approval.target_id == "MappingRule.update")
        )
        active = session.get(MappingRule, UUID(rule_id))
        assert approval is not None and approval.state == "pending"
        assert active is not None and active.status == "active"


def test_put_mapping_rule_requires_expected_version(json_client: TestClient, api_engine) -> None:
    rule_id, _ = _rule(api_engine, username="ing-rules-required-version")
    csrf = _login(json_client, "ing-rules-required-version")
    response = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf},
        json={"body": {"columns": {"orderId": "订单号"}}},
    )
    assert response.status_code == 422


def test_put_mapping_rule_rejects_client_controlled_verified_flag(
    json_client: TestClient, api_engine
) -> None:
    rule_id, _ = _rule(api_engine, username="ing-rules-verified")
    csrf = _login(json_client, "ing-rules-verified")
    response = json_client.put(
        f"/api/v1/ingest/mapping-rules/{rule_id}",
        headers={"X-CSRF-Token": csrf},
        json={
            "expectedVersion": 1,
            "verified": True,
            "body": {"columns": {"orderId": "订单号"}},
        },
    )
    assert response.status_code == 422
