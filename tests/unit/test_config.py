from pathlib import Path

from crosserp.config import load_settings
from crosserp.db.session import get_database_url


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
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path / "files"))
    settings = load_settings()
    assert settings.auth.max_failed_logins == 3
    assert settings.auth.session_hours == 24
    assert settings.auth.lockout_minutes == 15
    assert settings.audit_retention.security_days == 90
    assert settings.file_storage_dir == tmp_path / "files"


def test_isolated_database_and_files_stay_out_of_crosserp_home(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "isolated.db"
    files = tmp_path / "isolated-files"
    monkeypatch.setenv("CROSSERP_DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setenv("CROSSERP_MIGRATE_DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(files))
    settings = load_settings()
    forbidden = Path.home() / ".crosserp"
    assert not settings.file_storage_dir.is_relative_to(forbidden)
    assert forbidden.as_posix() not in get_database_url().replace("\\", "/")
