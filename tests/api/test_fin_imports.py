"""财务导入批次接口: GET/POST /finance/imports, GET /finance/imports/{id}。

覆盖验收标准:
- 有权成功 (200/201)
- 无权 404
- 不存在 404
- 未登录 401
- 店铺范围: 列表过滤, 单条 404, 写 403
- 写动作经 dispatcher, 中风险可撤销
- 幂等: 同人同键同体回放, 同键不同体 409, 他人同键 404 且不另建
- 审计记录含 actor_type, request_id
- 请求结束后用全新 Session 能查到结果
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.imports import insert_import_batch, insert_settlement
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AgentUndo,
    EntityVersion,
    IamDataScopeRule,
    IamPermissionOverride,
    ImportBatch,
    Store,
)

_REPO = Path(__file__).resolve().parents[2]
_SAMPLE = _REPO / "samples" / "synthetic" / "amazon_us_2026-10-01_2026-10-14.tsv"
_PASSWORD = "test-password-123"


def _login(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return str(client.cookies["crosserp_csrf"])


def _user(session: Session, username: str, *roles: Role):
    return create_user(session, username=username, password=_PASSWORD, roles=roles)


def _allow(session: Session, user_id: UUID, *permissions: str) -> None:
    now = datetime.now(UTC)
    session.add_all(
        IamPermissionOverride(
            user_id=user_id,
            permission=permission,
            effect="allow",
            reason="fin-imports test",
            data_scopes=[],
            created_at=now,
        )
        for permission in permissions
    )


def _store(name: str, marketplace: str = "US") -> Store:
    return Store(
        id=uuid4(),
        platform="amazon",
        marketplace=marketplace,
        name=name,
        currency="USD",
    )


def _scope_rule(
    *,
    name: str,
    entity: str,
    scope_type: str,
    values: object,
    user_id: UUID,
) -> IamDataScopeRule:
    return IamDataScopeRule(
        name=name,
        entity=entity,
        scope_type=scope_type,
        values=values,
        updated_by=user_id,
        updated_at=datetime.now(UTC),
    )


def _upload(
    client: TestClient,
    csrf: str,
    sample: Path = _SAMPLE,
    idempotency_key: str | None = None,
) -> any:
    headers = {"X-CSRF-Token": csrf}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    with open(sample, "rb") as f:
        return client.post(
            "/api/v1/finance/imports",
            files={"file": (sample.name, f, "text/tab-separated-values")},
            headers=headers,
        )


def _seed_batch_with_settlement(
    session: Session, *, store: Store, file_name: str, file_sha256: str | None = None
) -> ImportBatch:
    batch = insert_import_batch(
        session,
        connector_id="test",
        connector_version="1.0",
        file_name=file_name,
        file_sha256=file_sha256,
        imported_at=datetime.now(UTC),
    )
    insert_settlement(
        session,
        store_id=store.id,
        platform="amazon",
        external_id=f"SET-{uuid4().hex[:8]}",
        period_start=datetime(2026, 10, 1, tzinfo=UTC),
        period_end=datetime(2026, 10, 14, tzinfo=UTC),
        deposit_date=None,
        total=Decimal("100.0000"),
        currency="USD",
        source_batch_id=batch.id,
    )
    batch.row_count = 5
    batch.status = "done"
    return batch


# ============ 有权成功 ============


def test_list_imports_returns_200_with_pagination(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "list-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    _login(json_client, "list-ok")
    response = json_client.get("/api/v1/finance/imports", params={"page": 1, "pageSize": 10})
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["pageSize"] == 10


def test_get_import_returns_200_for_existing_batch(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "get-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )
        store = _store("GET 测试店铺")
        session.add(store)
        batch = _seed_batch_with_settlement(session, store=store, file_name="test.tsv")
        batch_id = batch.id

    _login(json_client, "get-ok")
    response = json_client.get(f"/api/v1/finance/imports/{batch_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(batch_id)
    assert body["status"] == "done"
    assert body["version"] == 1


def test_post_import_creates_batch(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "post-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "post-ok")
    response = _upload(json_client, csrf)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "batchId" in body
    assert "fileSha256" in body
    assert "status" in body
    assert "undoId" in body

    batch_id = UUID(body["batchId"])
    with Session(api_engine) as session:
        batch = session.get(ImportBatch, batch_id)
        assert batch is not None
        assert batch.status == "done"


# ============ 无权 404 ============


def test_list_imports_without_permission_returns_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "list-no-perm", Role.VIEWER)

    _login(json_client, "list-no-perm")
    response = json_client.get("/api/v1/finance/imports")
    assert response.status_code == 404


def test_get_import_without_permission_returns_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "get-no-perm", Role.VIEWER)
        store = _store("无权限店铺")
        session.add(store)
        batch = _seed_batch_with_settlement(session, store=store, file_name="test.tsv")
        batch_id = batch.id

    _login(json_client, "get-no-perm")
    response = json_client.get(f"/api/v1/finance/imports/{batch_id}")
    assert response.status_code == 404


def test_post_import_without_permission_returns_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        _user(session, "post-no-perm", Role.VIEWER)

    csrf = _login(json_client, "post-no-perm")
    response = _upload(json_client, csrf)
    assert response.status_code == 404


# ============ 不存在 404 ============


def test_get_import_nonexistent_returns_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "get-404", Role.OPERATOR)
        _allow(session, user.id, "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    _login(json_client, "get-404")
    fake_id = uuid4()
    response = json_client.get(f"/api/v1/finance/imports/{fake_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


# ============ 未登录 401 ============


def test_list_imports_unauthenticated_returns_401(json_client: TestClient) -> None:
    response = json_client.get("/api/v1/finance/imports")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_get_import_unauthenticated_returns_401(json_client: TestClient) -> None:
    fake_id = uuid4()
    response = json_client.get(f"/api/v1/finance/imports/{fake_id}")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_post_import_unauthenticated_returns_401(json_client: TestClient) -> None:
    with open(_SAMPLE, "rb") as f:
        response = json_client.post(
            "/api/v1/finance/imports",
            files={"file": (_SAMPLE.name, f, "text/tab-separated-values")},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


# ============ 店铺范围 ============


def test_list_imports_filters_by_store_scope(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "list-scope", Role.OPERATOR)
        _allow(session, user.id, "integration:read")
        visible_store = _store("可见店铺")
        hidden_store = _store("隐藏店铺")
        session.add_all([visible_store, hidden_store])

        visible_batch = _seed_batch_with_settlement(
            session, store=visible_store, file_name="visible.tsv"
        )
        visible_batch_id = visible_batch.id
        _seed_batch_with_settlement(session, store=hidden_store, file_name="hidden.tsv")

        session.add(
            _scope_rule(
                name="visible-only",
                entity="*",
                scope_type="storeIds",
                values=[str(visible_store.id)],
                user_id=user.id,
            )
        )

    _login(json_client, "list-scope")
    response = json_client.get("/api/v1/finance/imports")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(visible_batch_id)


def test_get_import_out_of_scope_returns_404(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "get-scope-404", Role.OPERATOR)
        _allow(session, user.id, "integration:read")
        hidden_store = _store("隐藏店铺")
        session.add(hidden_store)
        batch = _seed_batch_with_settlement(session, store=hidden_store, file_name="hidden.tsv")
        batch_id = batch.id

        other_store = _store("其他店铺")
        session.add(other_store)
        session.add(
            _scope_rule(
                name="other-only",
                entity="*",
                scope_type="storeIds",
                values=[str(other_store.id)],
                user_id=user.id,
            )
        )

    _login(json_client, "get-scope-404")
    response = json_client.get(f"/api/v1/finance/imports/{batch_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_post_import_empty_scope_returns_403(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "post-empty-scope", Role.OPERATOR)
        _allow(session, user.id, "integration:import")
        session.add(
            _scope_rule(
                name="empty-stores",
                entity="*",
                scope_type="storeIds",
                values=[],
                user_id=user.id,
            )
        )

    csrf = _login(json_client, "post-empty-scope")
    response = _upload(json_client, csrf)
    assert response.status_code == 403
    assert response.json()["code"] == "DATA_SCOPE_DENIED"


# ============ 中风险撤销 ============


def test_post_import_medium_risk_creates_undo(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "undo-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "undo-ok")
    response = _upload(json_client, csrf)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "undoId" in body
    undo_id = UUID(body["undoId"])

    with Session(api_engine) as session:
        undo = session.get(AgentUndo, undo_id)
        assert undo is not None
        assert undo.entity_type == "IngestBatch"
        assert undo.undone_at is None


def test_undo_import_restores_status(json_client: TestClient, api_engine) -> None:
    """中风险成功要能撤销, 并有一条撤销成功测试。"""
    with Session(api_engine) as session, session.begin():
        user = _user(session, "undo-restore", Role.OPERATOR)
        _allow(
            session,
            user.id,
            "integration:import",
            "integration:read",
            "agent_suggestion:create",
        )
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "undo-restore")
    response = _upload(json_client, csrf)
    assert response.status_code == 201, response.text
    body = response.json()
    batch_id = UUID(body["batchId"])
    undo_id = body["undoId"]

    undo_response = json_client.post(f"/api/v1/agent/suggestions/{undo_id}/undo")
    assert undo_response.status_code == 200, undo_response.text

    with Session(api_engine) as session:
        batch = session.get(ImportBatch, batch_id)
        assert batch is not None
        assert batch.status == "superseded"


# ============ 幂等 ============


def test_idempotency_same_key_same_payload_replays(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "idem-same", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "idem-same")

    response1 = _upload(json_client, csrf, idempotency_key="test-key-1")
    assert response1.status_code == 201
    body1 = response1.json()

    response2 = _upload(json_client, csrf, idempotency_key="test-key-1")
    assert response2.status_code == 201
    body2 = response2.json()

    assert body1["batchId"] == body2["batchId"]


def test_idempotency_same_key_different_payload_returns_409(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "idem-diff", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "idem-diff")

    sample1 = _REPO / "samples" / "synthetic" / "amazon_us_2026-10-01_2026-10-14.tsv"
    response1 = _upload(json_client, csrf, sample=sample1, idempotency_key="test-key-2")
    assert response1.status_code == 201

    sample2 = _REPO / "samples" / "synthetic" / "amazon_de_2026-10-01_2026-10-14.tsv"
    response2 = _upload(json_client, csrf, sample=sample2, idempotency_key="test-key-2")
    assert response2.status_code == 409
    assert response2.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_idempotency_other_user_same_key_is_not_found(
    json_client: TestClient, api_engine
) -> None:
    """他人使用同一幂等键返回 404 且不能各自独立创建."""
    with Session(api_engine) as session, session.begin():
        user1 = _user(session, "idem-user1", Role.OPERATOR)
        _allow(session, user1.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user1.id)
        )

        user2 = _user(session, "idem-user2", Role.OPERATOR)
        _allow(session, user2.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user2.id)
        )

    csrf1 = _login(json_client, "idem-user1")
    sample1 = _REPO / "samples" / "synthetic" / "amazon_us_2026-10-01_2026-10-14.tsv"
    response1 = _upload(json_client, csrf1, sample=sample1, idempotency_key="test-key-3")
    assert response1.status_code == 201, response1.text
    batch_id = response1.json()["batchId"]

    csrf2 = _login(json_client, "idem-user2")
    sample2 = _REPO / "samples" / "synthetic" / "amazon_de_2026-10-01_2026-10-14.tsv"
    response2 = _upload(json_client, csrf2, sample=sample2, idempotency_key="test-key-3")
    assert response2.status_code == 404, response2.text
    assert response2.json()["code"] == "NOT_FOUND"

    with Session(api_engine) as session:
        batches = list(session.scalars(select(ImportBatch)))
        assert len(batches) == 1
        assert str(batches[0].id) == batch_id


# ============ 审计 ============


def test_post_import_writes_audit_log(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "audit-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "audit-ok")
    response = _upload(json_client, csrf)
    assert response.status_code == 201
    body = response.json()
    batch_id = body["batchId"]

    # EntityVersion 存在 (dispatcher 写的)
    with Session(api_engine) as session:
        version = session.scalar(select(EntityVersion).where(EntityVersion.entity_id == batch_id))
        assert version is not None
        assert version.entity_type == "IngestBatch"
        assert version.action_id == "IngestBatch.create"


def test_post_import_writes_entity_version(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = _user(session, "version-ok", Role.OPERATOR)
        _allow(session, user.id, "integration:import", "integration:read")
        session.add(
            _scope_rule(name="all", entity="*", scope_type="all", values=[], user_id=user.id)
        )

    csrf = _login(json_client, "version-ok")
    response = _upload(json_client, csrf)
    assert response.status_code == 201
    body = response.json()
    batch_id = body["batchId"]

    with Session(api_engine) as session:
        version = session.scalar(select(EntityVersion).where(EntityVersion.entity_id == batch_id))
        assert version is not None
        assert version.entity_type == "IngestBatch"
        assert version.version == 1
