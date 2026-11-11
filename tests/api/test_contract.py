from pathlib import Path

import yaml

from scripts.check_api_contract import check_contract


def test_registered_api_routes_match_openapi(json_client) -> None:
    spec = yaml.safe_load(Path("docs/design/08/openapi-draft.yaml").read_text(encoding="utf-8"))
    errors = check_contract(json_client.app, spec)
    assert errors == []


def test_api_health_round_trip(json_client) -> None:
    response = json_client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == "test-request"


def test_approval_types_is_registered_once_before_id_route(json_client) -> None:
    from crosserp.api.routers import approvals

    routes = [
        route
        for route in approvals.router.routes
        if getattr(route, "path", None) == "/approvals/types"
        and getattr(route, "methods", set()) == {"GET"}
    ]
    assert len(routes) == 1
    ordered_paths = [getattr(route, "path", None) for route in approvals.router.routes]
    assert ordered_paths.index("/approvals/types") < ordered_paths.index("/approvals/{id}")


def test_approval_types_request_is_not_parsed_as_approval_id(json_client) -> None:
    from sqlalchemy.orm import Session

    from crosserp.auth.roles import Role
    from crosserp.db.repo.users import create_user
    from crosserp.platform.principal import Principal, get_principal

    with Session(json_client.app.state.database_engine) as session, session.begin():
        user = create_user(
            session,
            username="contract-admin",
            password="Contract-test-password-123",
            roles=(Role.ADMIN,),
        )
        user_id = user.id
    json_client.app.dependency_overrides[get_principal] = lambda: Principal(
        user_id=user_id, roles=frozenset({"admin"})
    )
    response = json_client.get("/api/v1/approvals/types")
    assert response.status_code == 200
    assert response.json()["items"] == []
