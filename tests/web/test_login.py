from html.parser import HTMLParser
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


class _HiddenInputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        data = dict(attrs)
        name = data.get("name")
        if name:
            self.values[name] = data.get("value") or ""


def _form_csrf(html: str) -> str:
    parser = _HiddenInputParser()
    parser.feed(html)
    return parser.values.get("csrf_token", "")


def test_browser_posts_token_from_login_html(tmp_path: Path) -> None:
    """先 GET 登录页, 只使用 HTML 隐藏字段里的令牌, 不从 cookie jar 另取."""
    client = _client(tmp_path)
    page = client.get("/login")
    token = _form_csrf(page.text)
    assert page.status_code == 200
    assert token
    assert token == client.cookies.get("crosserp_login_csrf")
    wrong = client.post(
        "/login",
        data={"username": "maken", "password": "wrong-password", "csrf_token": token},
    )
    assert wrong.status_code == 401
    assert "账号或密码错误。" in wrong.text
    assert "CSRF" not in wrong.text


def test_refresh_and_second_tab_keep_login_token(tmp_path: Path) -> None:
    client = _client(tmp_path)
    first = _form_csrf(client.get("/login").text)
    second = _form_csrf(client.get("/login").text)
    assert first
    assert first == second == client.cookies.get("crosserp_login_csrf")
    ok = client.post(
        "/login",
        data={
            "username": "maken",
            "password": "A-password-long",
            "csrf_token": first,
            "next": "/issues",
        },
        follow_redirects=False,
    )
    assert ok.status_code == 303
    assert client.get("/issues").status_code == 200


def test_login_error_page_keeps_submittable_token(tmp_path: Path) -> None:
    client = _client(tmp_path)
    token = _form_csrf(client.get("/login").text)
    failed = client.post(
        "/login",
        data={"username": "maken", "password": "wrong-password", "csrf_token": token},
    )
    assert failed.status_code == 401
    retry = _form_csrf(failed.text)
    assert retry
    assert retry == client.cookies.get("crosserp_login_csrf")
    ok = client.post(
        "/login",
        data={
            "username": "maken",
            "password": "A-password-long",
            "csrf_token": retry,
        },
        follow_redirects=False,
    )
    assert ok.status_code == 303


def test_malformed_login_csrf_cookie_is_replaced(tmp_path: Path) -> None:
    client = _client(tmp_path)
    page = client.get("/login", headers={"cookie": "crosserp_login_csrf=not-a-token"})
    token = _form_csrf(page.text)
    assert token
    assert "not-a-token" not in page.text
    assert token == client.cookies.get("crosserp_login_csrf")
    rejected = client.post(
        "/login",
        data={"username": "maken", "password": "wrong-password", "csrf_token": "not-a-token"},
    )
    assert rejected.status_code == 403
    wrong = client.post(
        "/login",
        data={"username": "maken", "password": "wrong-password", "csrf_token": token},
    )
    assert wrong.status_code == 401
    assert "账号或密码错误。" in wrong.text


def test_plain_text_csrf_errors_declare_utf8(tmp_path: Path) -> None:
    client = _client(tmp_path)
    responses = [
        client.post(
            "/login",
            data={
                "username": "maken",
                "password": "wrong-password",
                "csrf_token": "not-the-token",
            },
        ),
        client.post("/logout", data={"csrf_token": "not-the-token"}),
        client.post(
            "/profit/submit",
            data={"store": "s", "period": "2026-01", "csrf_token": "not-the-token"},
        ),
    ]
    for response in responses:
        assert response.status_code == 403
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.content.decode("utf-8") == "CSRF 校验失败"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_plain_text_errors_do_not_use_bare_response() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "crosserp" / "web" / "app.py"
    offenders = [
        f"{lineno}:{line.strip()}"
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1)
        if "return Response(" in line and line.strip() != "return Response(status_code=401)"
    ]
    assert offenders == []


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
