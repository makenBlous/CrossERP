"""init 首个管理员和幂等行为。"""

from __future__ import annotations

from typer.testing import CliRunner

from crosserp.auth.roles import Role
from crosserp.cli import app
from crosserp.db.schema import AppSetting, AppUser, AuditLog, UserRole
from crosserp.db.session import session_scope


def test_init_creates_admin_once(engine, monkeypatch) -> None:
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    runner = CliRunner()
    first = runner.invoke(
        app,
        [
            "init",
            "--admin-username",
            "maken",
            "--admin-password-stdin",
        ],
        input="A sufficiently long password\nA sufficiently long password\n",
    )
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, ["init"])
    assert second.exit_code == 0, second.output
    assert "管理员用户名" not in second.output
    with session_scope(engine) as session:
        user = session.query(AppUser).one()
        assert user.username == "maken"
        assert session.query(UserRole).filter_by(user_id=user.id).count() == len(Role)
        setting = session.get(AppSetting, "solo_mode")
        assert setting is not None and setting.value_json is True
        assert session.query(AuditLog).filter_by(action="user.create").count() == 1
