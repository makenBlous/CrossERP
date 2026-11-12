from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    ActionExecution,
    Approval,
    AuditLog,
    EntityVersion,
    IamDataScopeRule,
    Issue,
    Store,
    Voucher,
    VoucherLine,
    WorkflowRule,
)
from crosserp.platform.principal import ActorType, Principal, get_principal


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _user(session: Session, username: str, role: Role) -> None:
    create_user(session, username=username, password="Issue-test-password-1", roles=(role,))


def _store(name: str, currency: str = "USD") -> Store:
    return Store(platform="amazon", marketplace="US", name=name, currency=currency)


def _issue(store: Store, *, kind: str = "AMOUNT_MISMATCH", amount: str = "1.2345") -> Issue:
    return Issue(
        kind=kind,
        severity="error",
        detail_json={
            "store_id": str(store.id),
            "period": "2026-10",
            "diff": amount,
            "source_ref": f"{store.name}:{kind}",
            "order_id": f"ORDER-{store.name}",
            "sku": "SKU-1",
        },
        status="open",
        created_at=datetime.now(UTC),
    )


def _resolve_body(version: int = 0, resolution: str = "explained") -> dict[str, object]:
    return {
        "resolution": resolution,
        "reason": "平台费用差异已核对",
        "expectedVersion": version,
    }


def _headers(csrf: str, key: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "Idempotency-Key": key}


def test_issue_list_paginates_filters_and_keeps_money_precision(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "issue-reader", Role.ADMIN)
        visible = _store("可见店")
        hidden = _store("隐藏店", "EUR")
        session.add_all([visible, hidden])
        session.flush()
        first = _issue(visible, kind="AMOUNT_MISMATCH", amount="1.2345")
        second = _issue(visible, kind="NOT_IN_ERP", amount="-1.2300")
        third = _issue(hidden, kind="SKU_UNMAPPED", amount="0.0001")
        session.add_all([first, second, third])
        session.flush()
        visible_id = str(visible.id)

    _login(json_client, "issue-reader", "Issue-test-password-1")
    listed = json_client.get(
        "/api/v1/finance/issues",
        params={"page": 1, "pageSize": 1, "sort": "kind", "q": "可见店"},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 2
    assert body["pageSize"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["kind"] == "AMOUNT_MISMATCH"
    assert body["items"][0]["amount"] == {"amountMinor": 12345, "currency": "USD"}
    assert body["items"][0]["storeId"] == visible_id
    assert isinstance(body["items"][0]["amount"]["amountMinor"], int)

    negative = json_client.get("/api/v1/finance/issues", params={"q": "NOT_IN_ERP"})
    assert negative.json()["items"][0]["amount"]["amountMinor"] == -12300

    detail = json_client.get(f"/api/v1/finance/issues/{body['items'][0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["amount"]["amountMinor"] == 12345
    assert detail.json()["version"] == 0


def test_issue_reads_require_login_and_hide_missing_permission(
    json_client: TestClient, api_engine
) -> None:
    anonymous = json_client.get("/api/v1/finance/issues")
    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "AUTH_REQUIRED"

    with Session(api_engine) as session, session.begin():
        _user(session, "issue-nobody", Role.VIEWER)
        create_user(session, username="issue-empty", password="Issue-test-password-1")
        store = _store("读范围")
        session.add(store)
        session.flush()
        issue = _issue(store)
        session.add(issue)
        session.flush()
        issue_id = issue.id

    _login(json_client, "issue-empty", "Issue-test-password-1")
    assert json_client.get("/api/v1/finance/issues").status_code == 404
    assert json_client.get(f"/api/v1/finance/issues/{issue_id}").status_code == 404

    _login(json_client, "issue-nobody", "Issue-test-password-1")
    assert json_client.get("/api/v1/finance/issues").status_code == 200
    assert json_client.get(f"/api/v1/finance/issues/{uuid4()}").status_code == 404


def test_issue_data_scope_filters_reads_and_denies_writes(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="issue-scope",
            password="Issue-test-password-1",
            roles=(Role.ADMIN,),
        )
        visible = _store("范围店")
        hidden = _store("范围外")
        session.add_all([visible, hidden])
        session.flush()
        visible_issue = _issue(visible)
        hidden_issue = _issue(hidden)
        session.add_all([visible_issue, hidden_issue])
        session.add(
            IamDataScopeRule(
                name="issue-scope",
                entity="*",
                scope_type="storeIds",
                values=[str(visible.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        session.flush()
        visible_id = visible_issue.id
        hidden_id = hidden_issue.id

    csrf = _login(json_client, "issue-scope", "Issue-test-password-1")
    listed = json_client.get("/api/v1/finance/issues")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == str(visible_id)

    hidden_read = json_client.get(f"/api/v1/finance/issues/{hidden_id}")
    assert hidden_read.status_code == 404
    assert hidden_read.json()["code"] == "NOT_FOUND"

    denied = json_client.post(
        f"/api/v1/finance/issues/{hidden_id}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-scope-deny"),
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "DATA_SCOPE_DENIED"
    draft_denied = json_client.post(
        f"/api/v1/finance/issues/{hidden_id}/draft-voucher",
        json={"expectedVersion": 0},
        headers=_headers(csrf, "issue-scope-draft-deny"),
    )
    assert draft_denied.status_code == 403
    assert draft_denied.json()["code"] == "DATA_SCOPE_DENIED"


def test_resolve_changes_status_only_and_commits(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "issue-resolver", Role.ADMIN)
        store = _store("处理店")
        session.add(store)
        session.flush()
        issue = _issue(store, amount="8.5000")
        session.add(issue)
        session.flush()
        issue_id = issue.id

    csrf = _login(json_client, "issue-resolver", "Issue-test-password-1")
    response = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-resolve-1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "explained"
    assert body["version"] == 1
    assert body["undo"]["previous"]["status"] == "open"
    assert body["amount"]["amountMinor"] == 85000

    replay = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-resolve-1"),
    )
    assert replay.status_code == 200
    assert replay.json() == body

    conflict = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-resolve-conflict"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"

    with Session(api_engine) as session:
        stored = session.get(Issue, issue_id)
        assert stored is not None
        assert stored.status == "explained"
        assert stored.resolution_note == "平台费用差异已核对"
        version = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == "ReconIssue",
                EntityVersion.entity_id == str(issue_id),
            )
        )
        assert version is not None
        assert version.before_json["status"] == "open"
        assert version.after_json["status"] == "explained"
        assert session.scalar(select(func.count()).select_from(Voucher)) == 0

    ignored = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(version=1, resolution="ignored"),
        headers=_headers(csrf, "issue-resolve-ignore"),
    )
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "ignored"


def test_resolve_hides_unauthorized_replay_and_missing_key(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "issue-writer", Role.ADMIN)
        _user(session, "issue-viewer", Role.VIEWER)
        store = _store("回放店")
        session.add(store)
        session.flush()
        issue = _issue(store)
        session.add(issue)
        session.flush()
        issue_id = issue.id

    csrf = _login(json_client, "issue-writer", "Issue-test-password-1")
    first = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-replay-hidden"),
    )
    assert first.status_code == 200
    missing = json_client.post(
        f"/api/v1/finance/issues/{uuid4()}/resolve",
        json=_resolve_body(),
        headers=_headers(csrf, "issue-missing-write"),
    )
    assert missing.status_code == 404

    viewer_csrf = _login(json_client, "issue-viewer", "Issue-test-password-1")
    replay = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(viewer_csrf, "issue-replay-hidden"),
    )
    assert replay.status_code == 404
    assert replay.json()["code"] == "FORBIDDEN"
    draft = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/draft-voucher",
        json={"expectedVersion": 0},
        headers=_headers(viewer_csrf, "issue-viewer-draft"),
    )
    assert draft.status_code == 404

    writer_csrf = _login(json_client, "issue-writer", "Issue-test-password-1")
    no_key = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(version=1),
        headers={"X-CSRF-Token": writer_csrf},
    )
    assert no_key.status_code == 422
    json_client.cookies.clear()
    anonymous = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers={"Idempotency-Key": "issue-anon"},
    )
    assert anonymous.status_code == 401


def test_other_admin_does_not_receive_resolve_replay(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "issue-owner", Role.ADMIN)
        _user(session, "issue-peer", Role.ADMIN)
        store = _store("跨用户店")
        session.add(store)
        session.flush()
        issue = _issue(store)
        session.add(issue)
        session.flush()
        issue_id = issue.id

    owner_csrf = _login(json_client, "issue-owner", "Issue-test-password-1")
    first = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(owner_csrf, "issue-cross-user"),
    )
    assert first.status_code == 200
    peer_csrf = _login(json_client, "issue-peer", "Issue-test-password-1")
    replay = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers=_headers(peer_csrf, "issue-cross-user"),
    )
    assert replay.json() != first.json()
    assert replay.status_code == 409
    with Session(api_engine) as session, session.begin():
        session.execute(delete(ActionExecution))


def test_agent_resolve_executes_and_records_actor(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="issue-agent-user",
            password="Issue-test-password-1",
            roles=(Role.ADMIN,),
        )
        store = _store("智能体店")
        session.add(store)
        session.flush()
        issue = _issue(store)
        session.add(issue)
        session.flush()
        issue_id = issue.id
        user_id = user.id

    principal = Principal(
        user_id=user_id,
        actor_type=ActorType.AGENT,
        agent_id="recon-issue-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    json_client.app.dependency_overrides[get_principal] = lambda: principal
    response = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/resolve",
        json=_resolve_body(),
        headers={"Idempotency-Key": "issue-agent-resolve"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "explained"
    assert response.json()["undo"]["entity"] == "ReconIssue"
    with Session(api_engine) as session:
        version = session.scalar(
            select(EntityVersion).where(EntityVersion.entity_id == str(issue_id))
        )
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "ReconIssue.resolve"))
    assert version is not None
    assert version.actor_type == "agent"
    assert version.on_behalf_of == user_id
    assert version.before_json["status"] == "open"
    assert version.after_json["status"] == "explained"
    assert audit is not None
    assert audit.actor_type == "agent"
    assert str(audit.on_behalf_of) == str(user_id)


def test_human_draft_voucher_follows_approval_and_writes_draft_only(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "issue-draft-human", Role.ADMIN)
        _user(session, "issue-draft-approver", Role.FINANCE)
        store = _store("凭证店")
        session.add(store)
        session.flush()
        pending_issue = _issue(store, amount="2.5000")
        auto_issue = _issue(store, amount="3.0000")
        session.add_all([pending_issue, auto_issue])
        session.add(
            WorkflowRule(
                approval_type="reconissue",
                version=1,
                steps_json=[{"kind": "role", "role": "finance"}],
                enabled=True,
                updated_at=datetime.now(UTC),
            )
        )
        session.flush()
        pending_id = pending_issue.id
        auto_id = auto_issue.id

    csrf = _login(json_client, "issue-draft-human", "Issue-test-password-1")
    pending = json_client.post(
        f"/api/v1/finance/issues/{pending_id}/draft-voucher",
        json={"expectedVersion": 0},
        headers=_headers(csrf, "issue-draft-pending"),
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    assert pending.json()["approvalId"]
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(Voucher)) == 0
        stored = session.get(Issue, pending_id)
        assert stored is not None
        assert stored.status == "open"

    with Session(api_engine) as session, session.begin():
        rule = session.scalar(select(WorkflowRule))
        assert rule is not None
        rule.enabled = False

    drafted = json_client.post(
        f"/api/v1/finance/issues/{auto_id}/draft-voucher",
        json={"expectedVersion": 0, "reason": "生成调整草稿"},
        headers=_headers(csrf, "issue-draft-auto"),
    )
    assert drafted.status_code == 200
    assert drafted.json()["status"] == "draft"
    assert drafted.json()["amount"] == {"amountMinor": 30000, "currency": "USD"}
    voucher_id = UUID(drafted.json()["id"])
    with Session(api_engine) as session:
        voucher = session.get(Voucher, voucher_id)
        assert voucher is not None
        assert voucher.state == "draft"
        assert voucher.total_debit == Decimal("3.0000")
        assert voucher.total_credit == Decimal("3.0000")
        assert voucher.source_type == "issue"
        assert voucher.source_id == str(auto_id)
        lines = list(
            session.scalars(select(VoucherLine).where(VoucherLine.voucher_id == voucher.id))
        )
        assert {line.debit for line in lines} == {Decimal("3.0000"), Decimal(0)}
        issue = session.get(Issue, auto_id)
        assert issue is not None
        assert issue.status == "open"


def test_agent_draft_voucher_only_creates_approval(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="issue-draft-agent",
            password="Issue-test-password-1",
            roles=(Role.ADMIN,),
        )
        store = _store("审批店")
        session.add(store)
        session.flush()
        issue = _issue(store, amount="9.9900")
        session.add(issue)
        session.flush()
        issue_id = issue.id
        user_id = user.id

    principal = Principal(
        user_id=user_id,
        actor_type=ActorType.AGENT,
        agent_id="recon-draft-agent",
        on_behalf_of=user_id,
        channel="mcp",
    )
    json_client.app.dependency_overrides[get_principal] = lambda: principal
    response = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/draft-voucher",
        json={"expectedVersion": 0},
        headers={"Idempotency-Key": "issue-agent-draft"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_initiator"
    assert response.json()["approvalId"]
    assert "id" not in response.json()
    replay = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/draft-voucher",
        json={"expectedVersion": 0},
        headers={"Idempotency-Key": "issue-agent-draft"},
    )
    assert replay.status_code == 200
    assert replay.json() == response.json()
    conflict = json_client.post(
        f"/api/v1/finance/issues/{issue_id}/draft-voucher",
        json={"expectedVersion": 3},
        headers={"Idempotency-Key": "issue-agent-draft-conflict"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CONFLICT_VERSION"
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(Voucher)) == 0
        assert session.scalar(select(func.count()).select_from(EntityVersion)) == 0
        approval = session.scalar(select(Approval))
        stored = session.get(Issue, issue_id)
        assert approval is not None
        assert approval.state == "awaiting_initiator"
        assert approval.actor_type == "agent"
        assert approval.on_behalf_of == user_id
        assert stored is not None
        assert stored.status == "open"

    missing = json_client.post(
        f"/api/v1/finance/issues/{uuid4()}/draft-voucher",
        json={"expectedVersion": 0},
        headers={"Idempotency-Key": "issue-agent-missing"},
    )
    assert missing.status_code == 404
