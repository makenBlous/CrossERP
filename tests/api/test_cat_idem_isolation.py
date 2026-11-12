"""目录写接口按调用人隔离幂等回放。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import Store
from crosserp.db.session import sqlite_file_url
from crosserp.platform.principal import Principal, get_principal
from crosserp.web.app import create_app


@pytest.fixture
def catalog_app(tmp_path: Path) -> Iterator[tuple[TestClient, object]]:
    app = create_app(sqlite_file_url(tmp_path / "catalog-idem.db"))
    with TestClient(app) as client:
        yield client, app.state.database_engine
    app.state.database_engine.dispose()


def _admin(engine: object) -> Principal:
    with Session(engine) as session, session.begin():
        user = create_user(
            session,
            username=f"cat-idem-{uuid4().hex[:10]}",
            password="Catalog-idem-password-123",
        )
        grant_role(session, user.id, "admin")
        return Principal(user_id=user.id, roles=frozenset({"admin"}))


def _as(client: TestClient, principal: Principal) -> None:
    client.app.dependency_overrides[get_principal] = lambda: principal


def _store(engine: object) -> str:
    store_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            Store(
                id=store_id,
                platform="amazon",
                marketplace="US",
                name="idem-store",
                currency="USD",
            )
        )
    return str(store_id)


@pytest.mark.parametrize(
    "kind",
    ["category", "bundle", "cost", "listing", "mapping"],
)
def test_catalog_write_replay_is_isolated_by_caller(catalog_app, kind: str) -> None:
    client, engine = catalog_app
    owner = _admin(engine)
    peer = _admin(engine)
    store_id = _store(engine)
    bodies = {
        "category": ("/api/v1/catalog/categories", {"name": "隔离类目"}),
        "bundle": ("/api/v1/catalog/bundles", {"bundleSku": "ISO-BUNDLE", "components": []}),
        "cost": (
            "/api/v1/catalog/costs",
            {
                "internalSku": "ISO-SKU",
                "period": "2026-11",
                "unitCost": {"amountMinor": 10000, "currency": "CNY"},
                "source": "manual",
            },
        ),
        "listing": (
            "/api/v1/catalog/listings",
            {
                "storeId": store_id,
                "platformSku": "ISO-LIST",
                "price": {"amountMinor": 10000, "currency": "USD"},
            },
        ),
        "mapping": (
            "/api/v1/catalog/mappings",
            {
                "storeId": store_id,
                "platformSku": "ISO-MAP",
                "internalSku": "ISO-INT",
            },
        ),
    }
    path, body = bodies[kind]
    headers = {"Idempotency-Key": "catalog-shared-key"}

    _as(client, owner)
    created = client.post(path, json=body, headers=headers)
    assert created.status_code == 201, created.text

    _as(client, peer)
    peer_write = client.post(path, json=body, headers=headers)
    assert peer_write.json() != created.json()
    assert peer_write.status_code != 201 or peer_write.json()["id"] != created.json()["id"]

    _as(client, owner)
    replay = client.post(path, json=body, headers=headers)
    assert replay.status_code == 201
    assert replay.json() == created.json()
