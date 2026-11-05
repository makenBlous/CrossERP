from pathlib import Path

from fastapi.testclient import TestClient

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.session import make_engine, session_scope
from crosserp.web.app import create_app


def test_rows_whitelist_rejects_user_table(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'rows.sqlite'}"
    app = create_app(url)
    engine = make_engine(url)
    with session_scope(engine) as session:
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
    assert client.get("/rows/app_user/00000000-0000-0000-0000-000000000001").status_code == 404
