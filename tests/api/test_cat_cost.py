from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import AuditLog, EntityEvent, SkuCost
from crosserp.platform.approval import ApprovalResolution
from crosserp.platform.principal import ActorType, Principal, get_principal


def _app(api_database: str, principal: Principal):
    from crosserp.web.app import create_app

    app = create_app(api_database)
    app.dependency_overrides[get_principal] = lambda: principal
    return app


def _body(period: str = "2026-11") -> dict[str, object]:
    return {
        "internalSku": "SKU-1",
        "period": period,
        "unitCost": {"amountMinor": 125000, "currency": "CNY"},
        "source": "manual",
    }


def test_cost_list_is_paginated_and_returns_money(api_database: str) -> None:
    principal = Principal(user_id=uuid4(), permissions=frozenset({"item:read"}))
    app = _app(api_database, principal)
    with TestClient(app) as client:
        response = client.get("/api/v1/catalog/costs?page=1&pageSize=10")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "pageSize": 10, "total": 0}


def test_cost_create_writes_money_and_profit_recompute_event(
    api_database: str,
) -> None:
    principal = Principal(user_id=uuid4(), permissions=frozenset({"item:write", "item:read"}))
    app = _app(api_database, principal)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/catalog/costs",
            json=_body(),
            headers={"Idempotency-Key": "cost-create-1"},
        )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["unitCost"] == {"amountMinor": 125000, "currency": "CNY"}
    with Session(app.state.database_engine) as session:
        row = session.scalar(select(SkuCost))
        event = session.scalar(
            select(EntityEvent).where(EntityEvent.event_type == "profit.recompute_required")
        )
        assert row is not None and row.unit_cost == Decimal("12.5000")
        assert event is not None


def test_cost_period_overlap_is_rejected(api_database: str) -> None:
    principal = Principal(user_id=uuid4(), permissions=frozenset({"item:write"}))
    app = _app(api_database, principal)
    with TestClient(app) as client:
        assert client.post("/api/v1/catalog/costs", json=_body()).status_code == 201
        response = client.post("/api/v1/catalog/costs", json=_body())
    assert response.status_code == 422


def test_cost_no_permission_and_missing_principal_are_not_found(api_database: str) -> None:
    app = _app(api_database, Principal(user_id=uuid4()))
    with TestClient(app) as client:
        assert client.get("/api/v1/catalog/costs").status_code == 404
        assert client.post("/api/v1/catalog/costs", json=_body()).status_code == 404


def test_cost_agent_high_risk_waits_for_approval_without_writing(
    api_database: str,
) -> None:
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"item:write"}),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
    )
    app = _app(api_database, principal)
    with TestClient(app) as client:

        class Gateway:
            def submit(self, **_: object) -> object:
                return {
                    "approvalId": str(uuid4()),
                    "resolution": ApprovalResolution.AWAITING_INITIATOR,
                }

        app.state.approval_gateway = Gateway()
        response = client.post("/api/v1/catalog/costs", json=_body())
        assert response.status_code == 201
        assert response.json()["resolution"] == "awaiting_initiator"
    with Session(app.state.database_engine) as session:
        assert session.scalar(select(SkuCost)) is None
        audit = session.scalar(select(AuditLog))
        assert audit is not None and audit.actor_type == "agent"
        assert audit.after_json["on_behalf_of"] == str(principal.on_behalf_of)


def test_cost_idempotency_and_expected_version(api_database: str) -> None:
    principal = Principal(user_id=uuid4(), permissions=frozenset({"item:write"}))
    app = _app(api_database, principal)
    with TestClient(app) as client:
        headers = {"Idempotency-Key": "cost-replay"}
        first = client.post("/api/v1/catalog/costs", json=_body(), headers=headers)
        replay = client.post("/api/v1/catalog/costs", json=_body(), headers=headers)
        conflict = client.post(
            "/api/v1/catalog/costs",
            json={**_body("2026-12"), "expectedVersion": 1},
        )
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"


def test_cost_audit_keeps_actor_and_on_behalf_of(api_database: str) -> None:
    from crosserp.db.schema import AuditLog, EntityVersion

    represented = uuid4()
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"item:write"}),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=represented,
    )
    app = _app(api_database, principal)
    with TestClient(app) as client:
        principal = Principal(user_id=uuid4(), permissions=frozenset({"item:write"}))
        app.dependency_overrides[get_principal] = lambda: principal
        assert client.post("/api/v1/catalog/costs", json=_body()).status_code == 201
    with Session(app.state.database_engine) as session:
        version = session.scalar(select(EntityVersion))
        audit = session.scalar(select(AuditLog))
        assert version is not None and version.actor_type == "human"
        assert audit is not None
