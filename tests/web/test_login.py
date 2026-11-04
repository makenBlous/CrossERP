from pathlib import Path

from fastapi.testclient import TestClient

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.session import session_scope
from crosserp.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    url = f"sqlite:///{tmp_path / 'login.sqlite'}"
    app = create_app(url)
    from crosserp.db.session import make_engine

    engine = make_engine(url)
    with session_scope(engine) as session:
        create_user(session, username="maken", password="A-password-long", roles=tuple(Role))
    engine.dispose()
    return TestClient(app)


def test_login_cookie_and_csrf(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/issues", follow_redirects=False).status_code == 302
    page = client.get("/login")
    csrf = client.cookies.get("crosserp_login_csrf")
    assert page.status_code == 200 and csrf
    denied = client.post("/login", data={"username": "maken", "password": "A-password-long"})
    assert denied.status_code == 403
    response = client.post(
        "/login",
        data={
            "username": "maken",
            "password": "A-password-long",
            "csrf_token": csrf,
            "next": "/issues",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert client.get("/issues").status_code == 200
    assert (
        client.post(
            "/logout",
            data={"csrf_token": client.cookies.get("crosserp_csrf")},
            follow_redirects=False,
        ).status_code
        == 303
    )


def test_lockout_after_five_failures(tmp_path: Path) -> None:
    client = _client(tmp_path)
    csrf = client.get("/login").cookies.get("crosserp_login_csrf")
    data = {"username": "maken", "password": "wrong-password", "csrf_token": csrf}
    for _ in range(5):
        assert client.post("/login", data=data).status_code == 401
    response = client.post(
        "/login",
        data={**data, "password": "A-password-long"},
    )
    assert response.status_code == 401
