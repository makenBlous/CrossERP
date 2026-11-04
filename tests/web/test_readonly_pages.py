from fastapi.testclient import TestClient

from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.web.app import create_app


def test_readonly_pages_and_security_headers(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'web.sqlite'}"
    upgrade_head(url)
    application = create_app(url)
    client = TestClient(application)
    for path in ("/", "/imports", "/profit", "/issues"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"].startswith("/login")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"] == "default-src 'self'"
    assert all(
        set(getattr(route, "methods", set()) or ()) <= {"GET", "HEAD"}
        for route in application.routes
        if route.path in {"/", "/imports", "/profit", "/issues"}
    )
    downgrade_base(url)
