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
