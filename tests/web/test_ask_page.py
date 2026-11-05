from pathlib import Path

from fastapi.testclient import TestClient

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.session import make_engine, session_scope
from crosserp.web.app import create_app


def _login(client: TestClient, username: str) -> None:
    page = client.get("/login")
    client.post(
        "/login",
        data={
            "username": username,
            "password": "A-password-long",
            "csrf_token": page.cookies.get("crosserp_login_csrf"),
        },
    )


def test_ask_requires_ai_permission_and_missing_model_is_clear(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'ask.sqlite'}"
    app = create_app(url)
    engine = make_engine(url)
    with session_scope(engine) as session:
        create_user(
            session, username="operator", password="A-password-long", roles=(Role.OPERATOR,)
        )
        create_user(session, username="auditor", password="A-password-long", roles=(Role.AUDITOR,))
    engine.dispose()
    client = TestClient(app)
    _login(client, "operator")
    assert client.get("/ask").status_code == 200
    result = client.post(
        "/ask", data={"question": "测试", "csrf_token": client.cookies.get("crosserp_csrf")}
    )
    assert result.status_code == 503 and "CROSSERP_MODEL" in result.text
    client = TestClient(app)
    _login(client, "auditor")
    assert client.get("/ask").status_code == 403
