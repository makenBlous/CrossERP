from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, EntityEvent, IamPermissionOverride, SkuCost
from crosserp.platform.principal import ActorType, Principal, get_principal


def _app(api_database: str, principal: Principal):
    from crosserp.web.app import create_app

    app = create_app(api_database)
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"cost-{uuid4().hex}",
            password="Cost-test-password-123",
        )
        for permission in principal.permissions:
            session.add(
                IamPermissionOverride(
                    user_id=user.id,
                    permission=permission,
                    effect="allow",
                    reason="cost test",
                    data_scopes=[],
                    created_at=datetime.now(UTC),
                )
            )
        user_id = user.id
    principal = replace(
        principal,
        user_id=user_id,
        on_behalf_of=user_id if principal.is_agent else None,
    )
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
        response = client.post("/api/v1/catalog/costs", json=_body())
        assert response.status_code == 201
        assert response.json()["state"] == "awaiting_initiator"
    with Session(app.state.database_engine) as session:
        assert session.scalar(select(SkuCost)) is None
        audit = session.scalar(select(AuditLog))
        assert audit is not None and audit.actor_type == "agent"
        assert audit.on_behalf_of is not None


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
    from crosserp.db.schema import AuditLog

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
        assert client.post("/api/v1/catalog/costs", json=_body()).status_code == 201
    with Session(app.state.database_engine) as session:
        audit = session.scalar(select(AuditLog))
        assert audit is not None and audit.actor_type == "agent"
        assert audit.on_behalf_of is not None
