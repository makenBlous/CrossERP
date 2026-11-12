"""新建类动作撤销必须真正停用实体。空 before 不得记成成功。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE, restore_entity
from crosserp.db.migrate import upgrade_head
from crosserp.db.repo.users import create_user
from crosserp.db.schema import (
    AgentUndo,
    AuditLog,
    Brand,
    Bundle,
    Category,
    EntityVersion,
    IamDataScopeRule,
    IamPermissionOverride,
    Listing,
    Sku,
    SkuMapping,
    Store,
)
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.principal import Principal, get_principal
from crosserp.web.app import create_app


def _user(app, username: str, permissions: tuple[str, ...], store_ids: list[str]) -> Principal:
    with Session(app.state.database_engine) as session, session.begin():
        user = create_user(session, username=username, password="Undo-test-password-123")
        now = datetime.now(UTC)
        session.add_all(
            IamPermissionOverride(
                user_id=user.id,
                permission=permission,
                effect="allow",
                reason="create undo test",
                data_scopes=[],
                created_at=now,
            )
            for permission in permissions
        )
        session.add(
            IamDataScopeRule(
                name=f"{username}-stores",
                entity="*",
                scope_type="all" if not store_ids else "storeIds",
                values=store_ids,
                updated_by=user.id,
                updated_at=now,
            )
        )
        return Principal(user_id=user.id, permissions=frozenset(permissions))


def test_each_catalog_create_undo_deactivates_the_entity(api_database: str) -> None:
    app = create_app(api_database)
    principal = _user(
        app,
        "create-undo",
        (
            "brand:create",
            "brand:write",
            "brand:read",
            "item:create",
            "item:write",
            "item:delete",
            "item:read",
            "item_group:create",
            "item_group:write",
            "listing:create",
            "listing:write",
            "listing:read",
            "agent_suggestion:create",
        ),
        [],
    )
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        with Session(app.state.database_engine) as session, session.begin():
            store = Store(
                id=uuid4(), platform="amazon", marketplace="US", name="撤销店", currency="USD"
            )
            session.add(store)
            store_id = str(store.id)
        brand = client.post("/api/v1/catalog/brands", json={"name": "可撤销品牌"})
        sku = client.post(
            "/api/v1/catalog/skus",
            json={
                "internalSku": "INT-UNDO",
                "platformSku": "PLT-UNDO",
                "title": "可撤销 SKU",
                "active": True,
            },
        )
        bundle = client.post(
            "/api/v1/catalog/bundles",
            json={"bundleSku": "BUNDLE-UNDO", "components": []},
        )
        listing = client.post(
            "/api/v1/catalog/listings",
            json={
                "storeId": store_id,
                "platformSku": "LIST-UNDO",
                "price": {"amountMinor": 100, "currency": "USD"},
            },
        )
        category = client.post("/api/v1/catalog/categories", json={"name": "可撤销类目"})
        mapping = client.post(
            "/api/v1/catalog/mappings",
            json={"storeId": store_id, "platformSku": "MAP-UNDO", "internalSku": "INT-UNDO"},
        )
        created = {
            "brand": brand,
            "sku": sku,
            "bundle": bundle,
            "listing": listing,
            "category": category,
            "mapping": mapping,
        }
        for name, response in created.items():
            assert response.status_code == 201, f"{name}: {response.text}"
            assert response.json()["undoId"]
        for response in created.values():
            undone = client.post(f"/api/v1/agent/suggestions/{response.json()['undoId']}/undo")
            assert undone.status_code == 200, undone.text
            assert undone.json()["undone"] is True
    with Session(app.state.database_engine) as session:
        assert session.get(Brand, UUID(brand.json()["id"])).active is False
        assert session.get(Sku, UUID(sku.json()["id"])).active is False
        assert session.get(Bundle, UUID(bundle.json()["id"])).active is False
        assert session.get(Listing, UUID(listing.json()["id"])).status == "inactive"
        assert session.get(Category, UUID(category.json()["id"])).active is False
        assert session.get(SkuMapping, UUID(mapping.json()["id"])).state == "rejected"
        audits = list(
            session.scalars(select(AuditLog).where(AuditLog.action == "AgentSuggestion.undo"))
        )
        assert len(audits) == 6
        assert {row.actor_type for row in audits} == {"human"}


def test_brand_create_undo_requires_reverse_action_permission(api_database: str) -> None:
    app = create_app(api_database)
    principal = _user(
        app,
        "create-undo-denied",
        ("brand:create", "brand:read", "agent_suggestion:create"),
        [],
    )
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        created = client.post("/api/v1/catalog/brands", json={"name": "无权停用"})
        assert created.status_code == 201, created.text
        brand_id = created.json()["id"]
        denied = client.post(f"/api/v1/agent/suggestions/{created.json()['undoId']}/undo")
    assert denied.status_code == 404
    assert denied.json()["code"] == "FORBIDDEN"
    with Session(app.state.database_engine) as session:
        row = session.get(Brand, UUID(brand_id))
        assert row is not None and row.active is True
        assert session.scalar(select(AgentUndo).where(AgentUndo.undone_at.is_not(None))) is None
        assert (
            session.scalar(select(AuditLog).where(AuditLog.action == "AgentSuggestion.undo"))
            is None
        )


def test_listing_create_undo_rechecks_store_scope(api_database: str) -> None:
    app = create_app(api_database)
    principal = _user(
        app,
        "create-undo-scope",
        ("listing:create", "listing:write", "listing:read", "agent_suggestion:create"),
        [],
    )
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app) as client:
        with Session(app.state.database_engine) as session, session.begin():
            store_a = Store(
                id=uuid4(), platform="amazon", marketplace="US", name="A", currency="USD"
            )
            store_b = Store(
                id=uuid4(), platform="amazon", marketplace="DE", name="B", currency="EUR"
            )
            session.add_all([store_a, store_b])
            store_a_id = str(store_a.id)
            store_b_id = str(store_b.id)
        created = client.post(
            "/api/v1/catalog/listings",
            json={
                "storeId": store_b_id,
                "platformSku": "SCOPE-UNDO",
                "price": {"amountMinor": 100, "currency": "EUR"},
            },
        )
        assert created.status_code == 201, created.text
        listing_id = created.json()["id"]
        with Session(app.state.database_engine) as session, session.begin():
            rule = session.scalar(select(IamDataScopeRule))
            assert rule is not None
            rule.scope_type = "storeIds"
            rule.values = [store_a_id]
        denied = client.post(f"/api/v1/agent/suggestions/{created.json()['undoId']}/undo")
    assert denied.status_code == 403
    assert denied.json()["code"] == "DATA_SCOPE_DENIED"
    with Session(app.state.database_engine) as session:
        row = session.get(Listing, UUID(listing_id))
        assert row is not None and row.status == "active"


def test_restore_entity_rejects_before_without_restorable_fields(tmp_path: Path) -> None:
    url = sqlite_file_url(tmp_path / "empty-before.db")
    upgrade_head(url)
    engine = make_engine(url)
    brand_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(Brand(id=brand_id, name="kept", active=True, provenance={}))
        with pytest.raises(APIError) as empty:
            restore_entity(session, "Brand", str(brand_id), {})
        assert empty.value.code is ErrorCode.VALIDATION_FAILED
        with pytest.raises(APIError) as store_only:
            restore_entity(session, "Listing", str(uuid4()), {"storeId": str(uuid4())})
        assert store_only.value.code is ErrorCode.VALIDATION_FAILED
    with Session(engine) as session:
        assert session.get(Brand, brand_id).active is True
    engine.dispose()


class _Permissions:
    def require(self, principal: Principal, permission: str, _resource=None) -> None:
        if (
            permission not in {"public", "authenticated"}
            and permission not in principal.permissions
        ):
            raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

    def data_scope_filter(self, _principal: Principal, _entity: str) -> dict[str, bool]:
        return {"allowed": True}

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        return principal.permissions

    def store_scope(self, _principal: Principal, _entity: str):
        from crosserp.iam.scope import AllStores

        return AllStores()


def test_undo_with_empty_before_and_no_reverse_does_not_succeed(tmp_path: Path) -> None:
    url = sqlite_file_url(tmp_path / "empty-undo.db")
    upgrade_head(url)
    engine = make_engine(url)
    brand_id = uuid4()
    owner = uuid4()
    token_id = uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        session.add(Brand(id=brand_id, name="kept", active=True, provenance={}))
        session.add(
            EntityVersion(
                id=uuid4(),
                entity_type="Brand",
                entity_id=str(brand_id),
                version=1,
                changed_at=now,
                actor_type="human",
                actor_id=owner,
                action_id="Brand.create",
                before_json={},
                after_json={"name": "kept"},
                diff_json={},
            )
        )
        session.add(
            AgentUndo(
                id=token_id,
                entity_type="Brand",
                entity_id=str(brand_id),
                action_version=1,
                undo_payload_json={
                    "entity": "Brand",
                    "entityId": str(brand_id),
                    "action": "Brand.create",
                    "permission": "brand:create",
                    "before": {},
                    "actorId": str(owner),
                    "onBehalfOf": None,
                    "actorType": "human",
                    "reverseAction": None,
                    "reversePayload": None,
                    "reversePermission": None,
                },
                deadline_at=now + timedelta(hours=1),
            )
        )
    with Session(engine) as session, pytest.raises(APIError) as error, session.begin():
        make_action_dispatcher(
            session,
            _Permissions(),  # type: ignore[arg-type]
            undo_restore=CATALOG_UNDO_RESTORE,
        ).undo(
            token_id,
            principal=Principal(
                user_id=owner,
                permissions=frozenset({"brand:create", "brand:write", "agent_suggestion:create"}),
            ),
        )
    assert error.value.code is ErrorCode.VALIDATION_FAILED
    with Session(engine) as session:
        assert session.get(Brand, brand_id).active is True
        token = session.get(AgentUndo, token_id)
        assert token is not None and token.undone_at is None
        assert (
            session.scalar(select(AuditLog).where(AuditLog.action == "AgentSuggestion.undo"))
            is None
        )
    engine.dispose()


def test_action_dispatcher_is_constructed_only_by_factory() -> None:
    root = Path("src/crosserp")
    hits = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "ActionDispatcher(" in path.read_text(encoding="utf-8")
    ]
    assert hits == ["platform/factory.py"]
    platform = Path("src/crosserp/platform")
    for path in platform.rglob("*.py"):
        assert "crosserp.catalog" not in path.read_text(encoding="utf-8")
