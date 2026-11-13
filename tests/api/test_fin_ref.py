from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import AuditLog, FxRate, WorkflowRule
from crosserp.platform.principal import ActorType, Principal
from crosserp.vouchers.accounts import load_accounts


def _principal(*permissions: str, agent: bool = False) -> Principal:
    user_id = uuid4()
    return Principal(
        user_id=user_id,
        permissions=frozenset(permissions),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="fx-agent" if agent else None,
        on_behalf_of=user_id if agent else None,
        channel="mcp" if agent else "web",
    )


def _override(client: TestClient, principal: Principal, role: str | None) -> Principal:
    from crosserp.platform.principal import get_principal

    with Session(client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username=f"finref-{uuid4().hex}",
            password="Finref-test-password-123",
        )
        if role is not None:
            grant_role(session, user.id, role)
        user_id = user.id
    effective = replace(
        principal, user_id=user_id, on_behalf_of=user_id if principal.is_agent else None
    )
    client.app.dependency_overrides[get_principal] = lambda: effective
    return effective


_CHART = """
accounts:
  sales_revenue: {code: '待会计核实-销售收入', name: '销售收入', direction: credit}
  platform_fee: {code: '6001', name: '平台费用', direction: debit}
  ad_cost: {code: '待填-广告费', name: '广告费', direction: debit}
  fx_diff: {code: '6603', name: '汇兑差', direction: either}
  platform_receivable: {code: '1122', name: '平台应收', direction: either}
"""


def _rate_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "period": "2026-11",
        "fromCcy": "USD",
        "toCcy": "CNY",
        "rate": "7.12345678",
        "source": "用户提供",
    }
    body.update(overrides)
    return body


def test_accounts_marks_placeholders_and_paginates(
    json_client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "accounts.yaml"
    path.write_text(_CHART, encoding="utf-8")
    monkeypatch.setenv("CROSSERP_ACCOUNTS_FILE", str(path))
    _override(json_client, _principal("report:read"), "admin")

    listed = json_client.get(
        "/api/v1/finance/accounts",
        params={"q": "费", "page": 1, "pageSize": 1, "sort": "accountKey"},
    )
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 2
    assert page["page"] == 1
    assert page["pageSize"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["placeholder"] is True
    assert page["items"][0]["code"].startswith(("待填", "待会计核实"))

    full = json_client.get("/api/v1/finance/accounts", params={"pageSize": 50})
    assert full.status_code == 200
    by_key = {item["accountKey"]: item for item in full.json()["items"]}
    assert by_key["sales_revenue"]["placeholder"] is True
    assert by_key["sales_revenue"]["nameZh"] == "销售收入"
    assert by_key["platform_fee"]["placeholder"] is False
    assert by_key["platform_fee"]["direction"] == "debit"
    with pytest.raises(ValueError, match="待会计核实"):
        load_accounts(path)


def test_accounts_requires_permission(json_client: TestClient, tmp_path, monkeypatch) -> None:
    path = tmp_path / "accounts.yaml"
    path.write_text(_CHART, encoding="utf-8")
    monkeypatch.setenv("CROSSERP_ACCOUNTS_FILE", str(path))
    from crosserp.platform.principal import get_principal

    json_client.app.dependency_overrides.pop(get_principal, None)
    assert json_client.get("/api/v1/finance/accounts").status_code == 401

    _override(json_client, _principal(), None)
    assert json_client.get("/api/v1/finance/accounts").status_code == 404


def test_accounts_missing_file_is_explicit(
    json_client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CROSSERP_ACCOUNTS_FILE", str(tmp_path / "missing.yaml"))
    _override(json_client, _principal("report:read"), "admin")
    response = json_client.get("/api/v1/finance/accounts")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert "科目映射" in response.json()["message"]


def test_fx_rate_human_creates_commits_and_replays(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal("integration:write", "report:read"), "admin")
    created = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(),
        headers={"Idempotency-Key": "fx-create-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["applied"] is True
    assert body["state"] == "auto_effective"
    assert body["rate"] == "7.12345678"
    assert body["fromCcy"] == "USD"
    assert body["toCcy"] == "CNY"
    assert body["grain"] == "month"
    assert body["version"] == 1
    rate_id = body["id"]

    with Session(api_engine) as session:
        row = session.get(FxRate, UUID(rate_id))
        assert row is not None
        assert row.rate == Decimal("7.12345678")
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "FxRate.create").order_by(AuditLog.seq.desc())
        )
        assert audit is not None
        assert audit.actor_type == "human"
        assert audit.actor_user_id == principal.user_id
        assert audit.on_behalf_of is None

    replay = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(),
        headers={"Idempotency-Key": "fx-create-1"},
    )
    assert replay.status_code == 200
    assert replay.json() == body

    listed = json_client.get(
        "/api/v1/finance/fx-rates",
        params={"q": "USD", "page": 1, "pageSize": 1, "sort": "period"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == rate_id
    assert listed.json()["items"][0]["grain"] == "month"


def test_fx_rate_unauthorized_replay_is_not_found(json_client: TestClient) -> None:
    _override(json_client, _principal("integration:write"), "admin")
    created = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-10"),
        headers={"Idempotency-Key": "fx-hidden"},
    )
    assert created.status_code == 200

    _override(json_client, _principal(), None)
    denied = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-10"),
        headers={"Idempotency-Key": "fx-hidden"},
    )
    assert denied.status_code == 404

    from crosserp.platform.principal import get_principal

    json_client.app.dependency_overrides.pop(get_principal, None)
    assert json_client.post("/api/v1/finance/fx-rates", json=_rate_body()).status_code == 401
    assert json_client.get("/api/v1/finance/fx-rates").status_code == 401


def test_fx_rate_agent_only_creates_approval(json_client: TestClient, api_engine) -> None:
    principal = _override(json_client, _principal("integration:write", agent=True), "admin")
    response = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-09"),
        headers={"Idempotency-Key": "fx-agent-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "awaiting_initiator"
    assert body["applied"] is not True
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FxRate)) == 0
        audit = session.scalar(
            select(AuditLog).where(AuditLog.actor_type == "agent").order_by(AuditLog.seq.desc())
        )
        assert audit is not None
        assert audit.on_behalf_of == str(principal.user_id)
        assert audit.actor_user_id == principal.user_id

    replay = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-09"),
        headers={"Idempotency-Key": "fx-agent-1"},
    )
    assert replay.status_code == 200
    assert replay.json() == body
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FxRate)) == 0


def test_fx_rate_human_pending_does_not_write(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        approver = create_user(
            session,
            username=f"fin-approver-{uuid4().hex[:8]}",
            password="Finref-test-password-123",
        )
        grant_role(session, approver.id, "finance")
        session.add(
            WorkflowRule(
                id=uuid4(),
                approval_type="fxrate",
                version=1,
                steps_json=[{"kind": "role", "role": "finance"}],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
        )
    _override(json_client, _principal("integration:write"), "admin")
    response = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-08"),
        headers={"Idempotency-Key": "fx-pending-1"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "pending"
    assert response.json()["applied"] is False
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FxRate)) == 0


def test_fx_rate_expected_version_conflict(json_client: TestClient, api_engine) -> None:
    _override(json_client, _principal("integration:write"), "admin")
    created = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-07", rate="7.10000000"),
        headers={"Idempotency-Key": "fx-version-1"},
    )
    assert created.status_code == 200
    assert created.json()["version"] == 1

    conflict = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-07", rate="7.20000000", expectedVersion=9),
        headers={"Idempotency-Key": "fx-version-conflict"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"
    with Session(api_engine) as session:
        row = session.scalar(select(FxRate).where(FxRate.period == "2026-07"))
        assert row is not None
        assert row.rate == Decimal("7.10000000")

    updated = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-07", rate="7.20000000", expectedVersion=1),
        headers={"Idempotency-Key": "fx-version-2"},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["rate"] == "7.20000000"
    with Session(api_engine) as session:
        row = session.scalar(select(FxRate).where(FxRate.period == "2026-07"))
        assert row is not None
        assert row.rate == Decimal("7.20000000")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"rate": 7.1}, "十进制字符串"),
        ({"rate": "7.123456789"}, "小数位"),
        ({"rate": "0"}, "正数"),
        ({"rate": "-1.00000000"}, "正数"),
        ({"fromCcy": "ZZZ"}, "ISO 4217"),
        ({"fromCcy": "usd"}, "ISO 4217"),
        ({"period": "2026-13"}, "YYYY-MM"),
        ({"source": ""}, "source"),
    ],
)
def test_fx_rate_rejects_invalid_payload(
    json_client: TestClient, payload: dict[str, object], message: str
) -> None:
    _override(json_client, _principal("integration:write"), "admin")
    response = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(**payload),
        headers={"Idempotency-Key": f"fx-invalid-{uuid4().hex}"},
    )
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details", "requestId"}
    assert body["code"] == "VALIDATION_ERROR"
    assert message in body["message"] or message in response.text


def test_fx_rate_idempotency_mismatch(json_client: TestClient) -> None:
    _override(json_client, _principal("integration:write"), "admin")
    first = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-06"),
        headers={"Idempotency-Key": "fx-mismatch"},
    )
    assert first.status_code == 200
    conflict = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-06", rate="7.00000000"),
        headers={"Idempotency-Key": "fx-mismatch"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] in {"IDEMPOTENCY_REPLAY_MISMATCH", "IDEMPOTENCY_CONFLICT"}


def test_fx_rate_other_user_does_not_receive_replay(json_client: TestClient) -> None:
    _override(json_client, _principal("integration:write"), "admin")
    first = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-08"),
        headers={"Idempotency-Key": "fx-cross-user"},
    )
    assert first.status_code == 200
    _override(json_client, _principal("integration:write"), "admin")
    replay = json_client.post(
        "/api/v1/finance/fx-rates",
        json=_rate_body(period="2026-08"),
        headers={"Idempotency-Key": "fx-cross-user"},
    )
    assert replay.json() != first.json()
    assert replay.status_code == 400
    assert replay.json()["code"] == "VALIDATION_FAILED"
