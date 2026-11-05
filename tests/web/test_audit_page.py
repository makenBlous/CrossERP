from pathlib import Path

from fastapi.testclient import TestClient

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.session import make_engine, session_scope
from crosserp.web.app import create_app


def test_auditor_can_view_diff_and_viewer_is_denied(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'audit-web.sqlite'}"
    app = create_app(url)
    engine = make_engine(url)
    with session_scope(engine) as session:
        create_user(session, username="auditor", password="A-password-long", roles=(Role.AUDITOR,))
        create_user(session, username="viewer", password="A-password-long", roles=(Role.VIEWER,))
    engine.dispose()
    client = TestClient(app)

    page = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "viewer",
            "password": "A-password-long",
            "csrf_token": page.cookies.get("crosserp_login_csrf"),
        },
    )
    assert client.get("/audit").status_code == 403

    client = TestClient(app)
    page = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "auditor",
            "password": "A-password-long",
            "csrf_token": page.cookies.get("crosserp_login_csrf"),
        },
    )
    response = client.get("/audit")
    assert response.status_code == 200
    assert "改前/改后" in response.text
    assert client.get("/audit/verify").status_code == 200
