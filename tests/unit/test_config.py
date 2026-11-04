from pathlib import Path

from crosserp.config import load_settings


def test_environment_overrides_toml_and_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_dir = tmp_path / ".crosserp"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        "[auth]\nmax_failed_logins = 7\nsession_hours = 24\n"
        "[audit.retention]\nsecurity_days = 90\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CROSSERP_AUTH_MAX_FAILED_LOGINS", "3")
    settings = load_settings()
    assert settings.auth.max_failed_logins == 3
    assert settings.auth.session_hours == 24
    assert settings.auth.lockout_minutes == 15
    assert settings.audit_retention.security_days == 90
