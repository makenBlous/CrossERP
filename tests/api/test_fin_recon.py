"""对账运行 JSON 接口验收。"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import (
    Approval,
    AuditLog,
    EntityVersion,
    IamDataScopeRule,
    ImportBatch,
    Match,
    OrderLine,
    ReconRun,
    Store,
)
from crosserp.platform.principal import ActorType, Principal


def _principal(*permissions: str, agent: bool = False) -> Principal:
    user_id = uuid4()
    return Principal(
        user_id=user_id,
        permissions=frozenset(permissions),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="recon-agent" if agent else None,
        on_behalf_of=user_id if agent else None,
        channel="mcp" if agent else "web",
    )


def _override(client: TestClient, principal: Principal, role: str | None) -> Principal:
    from crosserp.platform.principal import get_principal

    with Session(client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"recon-{uuid4().hex}",
            password="Recon-test-password-123",
        )
        if role is not None:
            grant_role(session, user.id, role)
        user_id = user.id
    effective = replace(
        principal, user_id=user_id, on_behalf_of=user_id if principal.is_agent else None
    )
    client.app.dependency_overrides[get_principal] = lambda: effective
    return effective


def _store(session: Session, name: str) -> Store:
    row = Store(platform="amazon", marketplace="US", name=name, currency="USD")
    session.add(row)
    session.flush()
    return row


def _scope(
    session: Session, user_id: UUID, store_id: UUID, periods: list[str] | None = None
) -> None:
    now = datetime.now(UTC)
    session.add(
        IamDataScopeRule(
            name=f"recon-stores-{store_id}",
            entity="ReconRun",
            scope_type="storeIds",
            values=[str(store_id)],
            updated_by=user_id,
            updated_at=now,
        )
    )
    if periods is not None:
        session.add(
            IamDataScopeRule(
                name=f"recon-periods-{store_id}",
                entity="ReconRun",
                scope_type="periods",
                values=periods,
                updated_by=user_id,
                updated_at=now,
            )
        )


def test_recon_run_requires_login(json_client: TestClient) -> None:
    assert json_client.get("/api/v1/finance/recon-runs").status_code == 401
    assert json_client.get(f"/api/v1/finance/recon-runs/{uuid4()}").status_code == 401
    created = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(uuid4()), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-anon"},
    )
    assert created.status_code == 401
    assert created.json()["code"] == "AUTH_REQUIRED"


def test_recon_run_hides_unauthorized_and_missing(json_client: TestClient) -> None:
    _override(json_client, _principal(), None)
    assert json_client.get("/api/v1/finance/recon-runs").status_code == 404
    missing = str(uuid4())
    assert json_client.get(f"/api/v1/finance/recon-runs/{missing}").status_code == 404
    denied = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": missing, "period": "2026-10"},
        headers={"Idempotency-Key": "recon-denied"},
    )
    assert denied.status_code == 404
    assert denied.json()["code"] == "FORBIDDEN"


def test_recon_run_create_list_get_replay_and_commit(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal(), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        visible = _store(session, "可见店")
        hidden = _store(session, "范围外店")
        visible_id = visible.id
        hidden_id = hidden.id
        _scope(session, principal.user_id, visible_id, periods=["2026-10"])

    created = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(visible_id), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-create-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["storeId"] == str(visible_id)
    assert body["period"] == "2026-10"
    assert body["status"] == "done"
    assert body["version"] == 1
    assert body["matched"] == 0
    assert body["issues"] == 0
    assert body["matchRate"] is None
    assert isinstance(body["groupsTotal"], int)
    run_id = body["id"]

    with Session(api_engine) as fresh:
        stored = fresh.get(ReconRun, UUID(run_id))
        assert stored is not None
        assert stored.store_id == visible_id
        assert stored.period == "2026-10"
        assert stored.status == "done"

    replay = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(visible_id), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-create-1"},
    )
    assert replay.status_code == 200
    assert replay.json() == body
    with Session(api_engine) as fresh:
        assert fresh.scalar(select(func.count()).select_from(ReconRun)) == 1

    again = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(visible_id), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-create-2"},
    )
    assert again.status_code == 200
    assert again.json()["id"] != run_id

    listed = json_client.get(
        "/api/v1/finance/recon-runs",
        params={"q": "2026-10", "page": 1, "pageSize": 1, "sort": "-createdAt"},
    )
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["pageSize"] == 1
    assert {item["storeId"] for item in page["items"]} == {str(visible_id)}

    detail = json_client.get(f"/api/v1/finance/recon-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == run_id
    assert detail.json()["scope"] == {
        "storeId": str(visible_id),
        "period": "2026-10",
        "asOf": "2026-10-31",
    }

    hidden_write = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(hidden_id), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-hidden-store"},
    )
    assert hidden_write.status_code == 403
    assert hidden_write.json()["code"] == "DATA_SCOPE_DENIED"

    hidden_period = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(visible_id), "period": "2026-11"},
        headers={"Idempotency-Key": "recon-hidden-period"},
    )
    assert hidden_period.status_code == 403
    assert hidden_period.json()["code"] == "DATA_SCOPE_DENIED"

    missing_store = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(uuid4()), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-missing-store"},
    )
    assert missing_store.status_code == 404
    assert missing_store.json()["code"] == "NOT_FOUND"
    assert json_client.get(f"/api/v1/finance/recon-runs/{uuid4()}").status_code == 404
    missing_key = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(visible_id), "period": "2026-10"},
    )
    assert missing_key.status_code == 422
    assert missing_key.json()["code"] == "VALIDATION_FAILED"


def test_recon_run_filters_reads_by_data_scope(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal(), Role.VIEWER.value)
    with Session(api_engine) as session, session.begin():
        visible = _store(session, "可读店")
        hidden = _store(session, "不可读店")
        visible_id = visible.id
        hidden_id = hidden.id
        now = datetime.now(UTC)
        visible_run = ReconRun(
            store_id=visible_id,
            period="2026-10",
            as_of=date(2026, 10, 31),
            rule_set_version="test",
            started_at=now,
            finished_at=now,
            status="done",
            groups_total=0,
            groups_matched=0,
            non_order_lines=0,
        )
        hidden_run = ReconRun(
            store_id=hidden_id,
            period="2026-10",
            as_of=date(2026, 10, 31),
            rule_set_version="test",
            started_at=now,
            finished_at=now,
            status="done",
            groups_total=0,
            groups_matched=0,
            non_order_lines=0,
        )
        session.add_all([visible_run, hidden_run])
        session.flush()
        hidden_run_id = hidden_run.id
        _scope(session, principal.user_id, visible_id)

    listed = json_client.get("/api/v1/finance/recon-runs")
    assert listed.status_code == 200
    assert [item["storeName"] for item in listed.json()["items"]] == ["可读店"]
    assert json_client.get(f"/api/v1/finance/recon-runs/{hidden_run_id}").status_code == 404


def test_recon_run_unauthorized_replay_is_not_found(json_client: TestClient, api_engine) -> None:
    from crosserp.platform.principal import get_principal

    owner = _override(json_client, _principal(), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        store = _store(session, "回放店")
        store_id = store.id
    payload = {"storeId": str(store_id), "period": "2026-10"}
    headers = {"Idempotency-Key": "recon-replay-secret"}
    first = json_client.post("/api/v1/finance/recon-runs", json=payload, headers=headers)
    assert first.status_code == 200

    outsider = _principal()
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"recon-outsider-{uuid4().hex}",
            password="Recon-test-password-123",
        )
        outsider_id = user.id
    json_client.app.dependency_overrides[get_principal] = lambda: replace(
        outsider, user_id=outsider_id
    )
    replay = json_client.post("/api/v1/finance/recon-runs", json=payload, headers=headers)
    assert replay.status_code == 404
    assert replay.json()["code"] == "FORBIDDEN"
    assert owner.user_id != outsider_id


def test_cookie_user_without_write_permission_cannot_replay(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(
            session,
            username="recon-cookie-admin",
            password="Recon-test-password-123",
            roles=(Role.ADMIN,),
        )
        create_user(
            session,
            username="recon-cookie-viewer",
            password="Recon-test-password-123",
            roles=(Role.VIEWER,),
        )
        store = _store(session, "cookie店")
        store_id = store.id
    admin_login = json_client.post(
        "/api/v1/auth/login",
        json={"username": "recon-cookie-admin", "password": "Recon-test-password-123"},
    )
    assert admin_login.status_code == 200
    payload = {"storeId": str(store_id), "period": "2026-10"}
    headers = {
        "Idempotency-Key": "recon-cookie-replay",
        "X-CSRF-Token": json_client.cookies["crosserp_csrf"],
    }
    first = json_client.post("/api/v1/finance/recon-runs", json=payload, headers=headers)
    assert first.status_code == 200
    json_client.cookies.clear()
    viewer_login = json_client.post(
        "/api/v1/auth/login",
        json={"username": "recon-cookie-viewer", "password": "Recon-test-password-123"},
    )
    assert viewer_login.status_code == 200
    replay = json_client.post(
        "/api/v1/finance/recon-runs",
        json=payload,
        headers={
            "Idempotency-Key": "recon-cookie-replay",
            "X-CSRF-Token": json_client.cookies["crosserp_csrf"],
        },
    )
    assert replay.status_code == 404
    assert replay.json()["code"] == "FORBIDDEN"


def test_recon_run_agent_low_risk_executes_and_audits(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal(agent=True), Role.ADMIN.value)
    with Session(api_engine) as session, session.begin():
        store = _store(session, "智能体店")
        store_id = store.id

    response = json_client.post(
        "/api/v1/finance/recon-runs",
        json={"storeId": str(store_id), "period": "2026-10"},
        headers={"Idempotency-Key": "recon-agent-1"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "done"
    assert "approvalId" not in result
    with Session(api_engine) as session:
        version = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == "ReconRun",
                EntityVersion.entity_id == result["id"],
            )
        )
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "ReconRun.create")
            .order_by(AuditLog.seq.desc())
        )
        approvals = session.scalar(select(func.count()).select_from(Approval))
        stored = session.get(ReconRun, UUID(result["id"]))
    assert version is not None
    assert version.actor_type == "agent"
    assert version.on_behalf_of == principal.user_id
    assert audit is not None
    assert audit.actor_type == "agent"
    assert audit.on_behalf_of == str(principal.user_id)
    assert approvals == 0
    assert stored is not None


def test_recon_detail_amount_uses_minor_units(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal(), Role.VIEWER.value)
    with Session(api_engine) as session, session.begin():
        store = _store(session, "金额店")
        batch = ImportBatch(
            connector_id="test",
            connector_version="1",
            file_name="orders.csv",
            imported_at=datetime(2026, 10, 2, tzinfo=UTC),
            row_count=1,
            status="done",
            error_count=0,
        )
        session.add(batch)
        session.flush()
        order = OrderLine(
            store_id=store.id,
            platform_order_id="ORDER-1",
            platform_sku="SKU-1",
            qty=1,
            order_date=datetime(2026, 10, 2, tzinfo=UTC),
            item_price=Decimal("1.2345"),
            currency="USD",
            source_batch_id=batch.id,
        )
        run = ReconRun(
            store_id=store.id,
            period="2026-10",
            as_of=date(2026, 10, 31),
            rule_set_version="test",
            started_at=datetime(2026, 10, 31, tzinfo=UTC),
            finished_at=datetime(2026, 10, 31, tzinfo=UTC),
            status="done",
            groups_total=4,
            groups_matched=1,
            non_order_lines=0,
        )
        session.add_all([order, run])
        session.flush()
        session.add(
            Match(
                recon_run_id=run.id,
                order_line_id=order.id,
                rule_id="amount",
                status="matched",
                diff=Decimal("1.2345"),
                matched_at=datetime(2026, 10, 31, tzinfo=UTC),
            )
        )
        run_id = run.id

    detail = json_client.get(f"/api/v1/finance/recon-runs/{run_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["matchRate"] == "0.25"
    assert isinstance(payload["matchRate"], str)
    assert payload["matches"][0]["diff"] == {"amountMinor": 12345, "currency": "USD"}
    assert isinstance(payload["matches"][0]["diff"]["amountMinor"], int)

    listed = json_client.get("/api/v1/finance/recon-runs", params={"q": "金额店"})
    assert listed.status_code == 200
    assert listed.json()["items"][0]["matchRate"] == "0.25"
