"""导出产物列表。元数据、权限和店铺数据范围。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import Approval, AuditLog, ExportArtifact, IamDataScopeRule, Store, Voucher
from crosserp.platform.principal import ActorType, Principal


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _user(api_engine, username: str, *roles: Role):
    with Session(api_engine) as session, session.begin():
        return create_user(
            session,
            username=username,
            password="Export-test-password-123",
            roles=roles,
        ).id


def _approval(
    session: Session,
    *,
    target_type: str,
    target_id: str,
) -> Approval:
    row = Approval(
        target_type=target_type,
        target_id=target_id,
        state="approved",
        requested_by="operator",
        requested_at=datetime.now(UTC),
        actor_type="human",
    )
    session.add(row)
    session.flush()
    return row


def _artifact(
    session: Session,
    approval: Approval,
    *,
    target_id: str,
    file_name: str | None,
    sha256: str,
    created_at: datetime,
) -> ExportArtifact:
    row = ExportArtifact(
        approval_id=approval.id,
        target_id=target_id,
        file_path=None if file_name is None else f"exports/{file_name}",
        sha256=sha256,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def _store(session: Session, name: str, legal_entity: str) -> Store:
    row = Store(
        platform="amazon",
        marketplace="US",
        name=name,
        currency="USD",
        legal_entity=legal_entity,
    )
    session.add(row)
    session.flush()
    return row


def _voucher(session: Session, store: Store) -> Voucher:
    row = Voucher(
        store_id=store.id,
        period="2026-10",
        source_type="month",
        source_id=store.name,
        state="approved",
        currency="USD",
        total_debit=Decimal("12.3400"),
        total_credit=Decimal("12.3400"),
        inputs_hash="c" * 64,
        accounts_hash="d" * 64,
        created_by="operator",
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row


def test_export_list_returns_ledger_metadata_without_download(
    json_client: TestClient, api_engine
) -> None:
    _user(api_engine, "export-reader", Role.OPERATOR)
    created = datetime(2026, 10, 2, 3, 4, 5, tzinfo=UTC)
    with Session(api_engine) as session, session.begin():
        store = _store(session, "可见店", "账套甲")
        voucher = _voucher(session, store)
        approval = _approval(session, target_type="voucher", target_id=str(voucher.id))
        visible = _artifact(
            session,
            approval,
            target_id="kingdee_xlsx",
            file_name="kingdee-voucher.xlsx",
            sha256="a" * 64,
            created_at=created,
        )
        older = _artifact(
            session,
            _approval(session, target_type="profit_report", target_id="可见店:2026-10"),
            target_id="xlsx",
            file_name="profit-report.xlsx",
            sha256="b" * 64,
            created_at=created - timedelta(days=1),
        )
        nameless = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(voucher.id)),
            target_id="generic_xlsx",
            file_name=None,
            sha256="e" * 64,
            created_at=created + timedelta(hours=1),
        )
        _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(voucher.id)),
            target_id="not_a_ledger_target",
            file_name="other.bin",
            sha256="f" * 64,
            created_at=created,
        )
        visible_id = str(visible.id)
        older_id = str(older.id)
        nameless_id = str(nameless.id)
        approval_id = str(approval.id)
    _login(json_client, "export-reader", "Export-test-password-123")

    listed = json_client.get("/api/v1/finance/exports")
    assert listed.status_code == 200
    body = listed.json()
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["total"] == 3
    assert [item["exportId"] for item in body["items"]] == [nameless_id, visible_id, older_id]
    kingdee = body["items"][1]
    assert kingdee == {
        "exportId": visible_id,
        "target": "kingdee_xlsx",
        "fileName": "kingdee-voucher.xlsx",
        "sha256": "a" * 64,
        "approvalId": approval_id,
        "createdAt": created.isoformat(),
    }
    assert body["items"][0]["fileName"] is None
    assert "filePath" not in kingdee
    assert "downloadUrl" not in kingdee
    assert "exports/kingdee-voucher.xlsx" not in listed.text
    assert "amount" not in listed.text

    page = json_client.get("/api/v1/finance/exports", params={"page": 2, "pageSize": 1})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert [item["exportId"] for item in page.json()["items"]] == [visible_id]

    found = json_client.get("/api/v1/finance/exports", params={"q": "KINGDEE-voucher"})
    assert found.status_code == 200
    assert [item["exportId"] for item in found.json()["items"]] == [visible_id]

    by_hash = json_client.get("/api/v1/finance/exports", params={"q": "b" * 8})
    assert [item["exportId"] for item in by_hash.json()["items"]] == [older_id]

    ordered = json_client.get("/api/v1/finance/exports", params={"sort": "createdAt"})
    assert [item["exportId"] for item in ordered.json()["items"]] == [
        older_id,
        visible_id,
        nameless_id,
    ]
    by_target = json_client.get("/api/v1/finance/exports", params={"sort": "target"})
    assert [item["target"] for item in by_target.json()["items"]] == [
        "generic_xlsx",
        "kingdee_xlsx",
        "xlsx",
    ]


def test_export_list_filters_store_and_account_book_scope(
    json_client: TestClient, api_engine
) -> None:
    user_id = _user(api_engine, "export-scope", Role.OPERATOR)
    created = datetime(2026, 10, 3, tzinfo=UTC)
    with Session(api_engine) as session, session.begin():
        visible = _store(session, "范围内", "账套甲")
        hidden = _store(session, "范围外", "账套乙")
        same_book = _store(session, "同账套另一店", "账套甲")
        wrong_book = _store(session, "店在范围账套不对", "账套乙")
        visible_voucher = _voucher(session, visible)
        hidden_voucher = _voucher(session, hidden)
        book_voucher = _voucher(session, same_book)
        wrong_book_voucher = _voucher(session, wrong_book)
        visible_artifact = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(visible_voucher.id)),
            target_id="kingdee_xlsx",
            file_name="visible.xlsx",
            sha256="1" * 64,
            created_at=created,
        )
        hidden_artifact = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(hidden_voucher.id)),
            target_id="generic_xlsx",
            file_name="hidden.xlsx",
            sha256="2" * 64,
            created_at=created,
        )
        profit = _artifact(
            session,
            _approval(session, target_type="profit_report", target_id="范围内:2026-10"),
            target_id="xlsx",
            file_name="profit.xlsx",
            sha256="3" * 64,
            created_at=created,
        )
        hidden_profit = _artifact(
            session,
            _approval(session, target_type="profit_report", target_id="范围外:2026-09"),
            target_id="xlsx",
            file_name="hidden-profit.xlsx",
            sha256="4" * 64,
            created_at=created,
        )
        unaffiliated = _artifact(
            session,
            _approval(session, target_type="import_batch", target_id="batch-1"),
            target_id="kingdee_xlsx",
            file_name="no-store.xlsx",
            sha256="5" * 64,
            created_at=created,
        )
        missing_voucher = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(uuid4())),
            target_id="kingdee_xlsx",
            file_name="missing-voucher.xlsx",
            sha256="6" * 64,
            created_at=created,
        )
        book_only = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(book_voucher.id)),
            target_id="generic_xlsx",
            file_name="same-book.xlsx",
            sha256="7" * 64,
            created_at=created,
        )
        wrong_book_artifact = _artifact(
            session,
            _approval(session, target_type="voucher", target_id=str(wrong_book_voucher.id)),
            target_id="kingdee_xlsx",
            file_name="wrong-book.xlsx",
            sha256="9" * 64,
            created_at=created,
        )
        session.add(
            IamDataScopeRule(
                name="export-store-scope",
                entity="ExportPackage",
                scope_type="storeIds",
                values=[str(visible.id), str(wrong_book.id)],
                updated_by=user_id,
                updated_at=datetime.now(UTC),
            )
        )
        session.add(
            IamDataScopeRule(
                name="export-book-scope",
                entity="ExportPackage",
                scope_type="legalEntities",
                values=["账套甲"],
                updated_by=user_id,
                updated_at=datetime.now(UTC),
            )
        )
        expected = {str(visible_artifact.id), str(profit.id), str(unaffiliated.id)}
        hidden_ids = {
            str(hidden_artifact.id),
            str(hidden_profit.id),
            str(missing_voucher.id),
            str(book_only.id),
            str(wrong_book_artifact.id),
        }
    _login(json_client, "export-scope", "Export-test-password-123")

    response = json_client.get("/api/v1/finance/exports", params={"pageSize": 50})
    assert response.status_code == 200
    found = {item["exportId"] for item in response.json()["items"]}
    assert found == expected
    assert found.isdisjoint(hidden_ids)

    leaked = json_client.get("/api/v1/finance/exports", params={"q": "hidden.xlsx"})
    assert leaked.status_code == 200
    assert leaked.json()["items"] == []
    assert leaked.json()["total"] == 0


def test_export_list_hides_unauthorized_and_requires_login(
    json_client: TestClient, api_engine
) -> None:
    anonymous = json_client.get("/api/v1/finance/exports")
    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "AUTH_REQUIRED"

    _user(api_engine, "export-none")
    _login(json_client, "export-none", "Export-test-password-123")
    denied = json_client.get(
        "/api/v1/finance/exports", headers={"Idempotency-Key": "exports-denied"}
    )
    replay = json_client.get(
        "/api/v1/finance/exports", headers={"Idempotency-Key": "exports-denied"}
    )
    assert denied.status_code == replay.status_code == 404
    assert denied.json()["code"] == "FORBIDDEN"


def test_export_agent_reads_without_audit_or_mutation(
    json_client: TestClient, api_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = _user(api_engine, "export-agent", Role.VIEWER)
    with Session(api_engine) as session, session.begin():
        approval = _approval(session, target_type="import_batch", target_id="batch-agent")
        artifact = _artifact(
            session,
            approval,
            target_id="xlsx",
            file_name="agent.xlsx",
            sha256="8" * 64,
            created_at=datetime(2026, 10, 4, tzinfo=UTC),
        )
        artifact_id = str(artifact.id)
        before = session.scalar(select(func.count()).select_from(ExportArtifact))
        audit_before = session.scalar(select(func.count()).select_from(AuditLog))
    _login(json_client, "export-agent", "Export-test-password-123")
    monkeypatch.setattr(
        "crosserp.api.routers._platform_common.get_principal",
        lambda _request: Principal(
            user_id=user_id,
            roles=frozenset({Role.VIEWER.value}),
            actor_type=ActorType.AGENT,
            agent_id="export-agent",
            on_behalf_of=user_id,
            channel="mcp",
        ),
    )

    response = json_client.get("/api/v1/finance/exports")

    assert response.status_code == 200
    assert [item["exportId"] for item in response.json()["items"]] == [artifact_id]
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(ExportArtifact)) == before
        assert session.scalar(select(func.count()).select_from(AuditLog)) == audit_before


def test_export_list_rejects_invalid_sort_and_page_size(
    json_client: TestClient, api_engine
) -> None:
    _user(api_engine, "export-sort", Role.OPERATOR)
    _login(json_client, "export-sort", "Export-test-password-123")

    invalid = json_client.get("/api/v1/finance/exports", params={"sort": "sha256"})
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "VALIDATION_FAILED"

    oversized = json_client.get("/api/v1/finance/exports", params={"pageSize": 201})
    assert oversized.status_code == 422
    assert oversized.json()["code"] == "VALIDATION_ERROR"
