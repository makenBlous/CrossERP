"""DocumentLink 平台底座接口验收。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.api.routers import _platform_common, documents
from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import DocumentLink, IamDataScopeRule, Store


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _link(from_type: str, from_id: str, to_type: str, to_id: str, relation: str) -> DocumentLink:
    return DocumentLink(
        id=uuid4(),
        from_type=from_type,
        from_id=from_id,
        to_type=to_type,
        to_id=to_id,
        relation=relation,
        created_at=datetime.now(UTC),
    )


def test_document_routes_are_discovered_from_documents_module() -> None:
    platform_paths = {route.path for route in _platform_common.router.routes}
    document_paths = {route.path for route in documents.router.routes}

    assert "/documents/links" not in platform_paths
    assert "/documents/chain/{docType}/{id}" not in platform_paths
    assert document_paths == {"/documents/links", "/documents/chain/{docType}/{id}"}


def test_document_links_filter_by_store_scope(json_client: TestClient, api_engine) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="document-scope-user", password="abcdefghij", roles=(Role.OPERATOR,)
        )
        visible_store = Store(
            id=uuid4(), platform="amazon", marketplace="US", name="visible", currency="USD"
        )
        hidden_store = Store(
            id=uuid4(), platform="amazon", marketplace="DE", name="hidden", currency="EUR"
        )
        session.add_all([visible_store, hidden_store])
        session.add_all(
            [
                _link("Store", str(visible_store.id), "Order", "order-visible", "creates"),
                _link("Order", "order-visible", "Settlement", "settlement-visible", "settles"),
                _link("Store", str(hidden_store.id), "Order", "order-hidden", "creates"),
            ]
        )
        session.add(
            IamDataScopeRule(
                name="document-scope",
                entity="*",
                scope_type="storeIds",
                values=[str(visible_store.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        visible_store_id = str(visible_store.id)

    _login(json_client, "document-scope-user", "abcdefghij")
    response = json_client.get(
        "/api/v1/documents/links", params={"q": "creates", "page": 1, "pageSize": 1}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["from"]["id"] == visible_store_id
    assert set(response.json()["items"][0]) == {"id", "from", "to", "relation"}
    downstream = json_client.get("/api/v1/documents/links", params={"q": "settlement"})
    assert downstream.json()["total"] == 1
    default_page = json_client.get("/api/v1/documents/links")
    assert default_page.json()["pageSize"] == 20
    assert default_page.json()["total"] == 2


def test_document_api_metadata_matches_contract(json_client: TestClient) -> None:
    paths = json_client.app.openapi()["paths"]

    assert paths["/api/v1/documents/links"]["get"]["x-crosserp"] == {
        "entity": "DocumentLink",
        "action": "DocumentLink.read_links",
        "permission": "document:read",
        "riskTier": "none",
    }
    assert paths["/api/v1/documents/chain/{docType}/{id}"]["get"]["x-crosserp"] == {
        "entity": "DocumentLink",
        "action": "DocumentLink.read_chain",
        "permission": "report:read",
        "riskTier": "none",
    }


def test_document_chain_hides_unauthorized_nodes_and_deduplicates_cycles(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session, username="document-chain-user", password="abcdefghij", roles=(Role.OPERATOR,)
        )
        visible_store = Store(
            id=uuid4(), platform="amazon", marketplace="US", name="visible", currency="USD"
        )
        hidden_store = Store(
            id=uuid4(), platform="amazon", marketplace="DE", name="hidden", currency="EUR"
        )
        session.add_all([visible_store, hidden_store])
        session.add_all(
            [
                _link("Store", str(visible_store.id), "Order", "order-visible", "creates"),
                _link("Order", "order-visible", "Settlement", "settlement-visible", "settles"),
                _link(
                    "Settlement", "settlement-visible", "Store", str(visible_store.id), "returns"
                ),
                _link("Order", "order-visible", "Store", str(hidden_store.id), "leaks"),
            ]
        )
        session.add(
            IamDataScopeRule(
                name="document-chain-scope",
                entity="*",
                scope_type="storeIds",
                values=[str(visible_store.id)],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        visible_store_id = str(visible_store.id)
        hidden_store_id = str(hidden_store.id)

    _login(json_client, "document-chain-user", "abcdefghij")
    response = json_client.get(f"/api/v1/documents/chain/Store/{visible_store_id}")

    assert response.status_code == 200
    links = response.json()["links"]
    assert len(links) == 3
    assert all(hidden_store_id not in link.values() for link in links)


def test_document_chain_returns_not_found_for_unknown_or_hidden_root(
    json_client: TestClient, api_engine
) -> None:
    with Session(api_engine) as session, session.begin():
        user = create_user(
            session,
            username="document-not-found-user",
            password="abcdefghij",
            roles=(Role.OPERATOR,),
        )
        hidden_store = Store(
            id=uuid4(), platform="amazon", marketplace="DE", name="hidden", currency="EUR"
        )
        session.add(hidden_store)
        session.add(_link("Store", str(hidden_store.id), "Order", "hidden-order", "creates"))
        session.add(
            IamDataScopeRule(
                name="document-hidden-scope",
                entity="*",
                scope_type="storeIds",
                values=[str(uuid4())],
                updated_by=user.id,
                updated_at=datetime.now(UTC),
            )
        )
        hidden_store_id = str(hidden_store.id)

    _login(json_client, "document-not-found-user", "abcdefghij")
    hidden = json_client.get(f"/api/v1/documents/chain/Store/{hidden_store_id}")
    unknown = json_client.get("/api/v1/documents/chain/Order/does-not-exist")

    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json()["code"] == unknown.json()["code"] == "NOT_FOUND"


def test_document_links_require_authentication(json_client: TestClient) -> None:
    response = json_client.get("/api/v1/documents/links")
    chain = json_client.get("/api/v1/documents/chain/Order/does-not-exist")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"
    assert chain.status_code == 401
    assert chain.json()["code"] == "AUTH_REQUIRED"
