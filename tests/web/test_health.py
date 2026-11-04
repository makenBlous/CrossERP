"""首页与健康检查。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from typer.testing import CliRunner

from crosserp import __version__
from crosserp.cli import app
from crosserp.web.app import create_app


def test_health_ok() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
    assert "db" not in response.json()


def test_index_shows_running() -> None:
    response = TestClient(create_app()).get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith("/login")


def test_htmx_static_served() -> None:
    response = TestClient(create_app()).get("/static/htmx.min.js")
    assert response.status_code == 200
    assert "htmx" in response.text


def test_serve_is_always_localhost(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_run(application: object, *, host: str, port: int) -> None:
        assert application is not None
        calls.append((host, port))

    monkeypatch.setattr("crosserp.cli.uvicorn.run", fake_run)
    runner = CliRunner()

    local = runner.invoke(app, ["serve"])
    assert local.exit_code == 0
    assert "对外开放前请配置 HTTPS 和登录（v0.5）" not in local.stdout  # noqa: RUF001
    assert calls == [("127.0.0.1", 8000)]

    public = runner.invoke(app, ["serve", "--port", "8000"])
    assert public.exit_code == 0
    assert calls == [("127.0.0.1", 8000), ("127.0.0.1", 8000)]
