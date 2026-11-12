"""CrossERP 运行配置。环境变量优先于用户配置文件和默认值。"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AuthSettings(BaseModel):
    max_failed_logins: int = Field(default=5, ge=1)
    lockout_minutes: int = Field(default=15, ge=1)
    session_hours: int = Field(default=12, ge=1)
    idle_hours: int = Field(default=2, ge=1)


class AuditRetentionSettings(BaseModel):
    business: str = "never"
    security_days: int = Field(default=180, ge=1)


class AiSettings(BaseModel):
    text_days: int = Field(default=90, ge=1)


def default_database_file() -> Path:
    """默认数据库文件。文件目录默认放在同一目录, 只在这里定义。"""
    return Path.home() / ".crosserp" / "data.db"


def default_files_dir() -> Path:
    return default_database_file().parent / "files"


class FilesSettings(BaseModel):
    directory: Path = Field(default_factory=default_files_dir)


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    auth: AuthSettings = Field(default_factory=AuthSettings)
    audit_retention: AuditRetentionSettings = Field(default_factory=AuditRetentionSettings)
    cookie_secure: bool = False
    ai: AiSettings = Field(default_factory=AiSettings)
    file_storage_dir: Path


def load_settings(*, file_storage_dir: str | Path | None = None) -> Settings:
    raw: dict[str, object] = {}
    path = Path.home() / ".crosserp" / "config.toml"
    if path.is_file():
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    auth_raw = raw.get("auth")
    auth = {str(k): v for k, v in auth_raw.items()} if isinstance(auth_raw, dict) else {}
    audit_raw = raw.get("audit")
    retention_raw = audit_raw.get("retention") if isinstance(audit_raw, dict) else None
    retention = (
        {str(k): v for k, v in retention_raw.items()} if isinstance(retention_raw, dict) else {}
    )
    env = os.environ
    updates = {
        "max_failed_logins": env.get("CROSSERP_AUTH_MAX_FAILED_LOGINS"),
        "lockout_minutes": env.get("CROSSERP_AUTH_LOCKOUT_MINUTES"),
        "session_hours": env.get("CROSSERP_AUTH_SESSION_HOURS"),
        "idle_hours": env.get("CROSSERP_AUTH_IDLE_HOURS"),
    }
    auth_data = AuthSettings(**auth).model_dump()
    auth_data.update({k: int(v) for k, v in updates.items() if v is not None})
    retention_data = AuditRetentionSettings(**retention).model_dump()
    if env.get("CROSSERP_AUDIT_RETENTION_BUSINESS") is not None:
        retention_data["business"] = env["CROSSERP_AUDIT_RETENTION_BUSINESS"]
    if env.get("CROSSERP_AUDIT_RETENTION_SECURITY_DAYS") is not None:
        retention_data["security_days"] = int(env["CROSSERP_AUDIT_RETENTION_SECURITY_DAYS"])
    secure = env.get("CROSSERP_COOKIE_SECURE")
    ai_raw = raw.get("ai")
    ai_data = {str(k): v for k, v in ai_raw.items()} if isinstance(ai_raw, dict) else {}
    if env.get("CROSSERP_AI_RETENTION_TEXT_DAYS") is not None:
        ai_data["text_days"] = int(env["CROSSERP_AI_RETENTION_TEXT_DAYS"])
    files = FilesSettings.model_validate(raw.get("files", {}))
    directory = files.directory
    if env.get("CROSSERP_FILES_DIR"):
        directory = Path(env["CROSSERP_FILES_DIR"])
    if file_storage_dir is not None:
        directory = Path(file_storage_dir)
    return Settings(
        auth=AuthSettings(**auth_data),
        audit_retention=AuditRetentionSettings(**retention_data),
        cookie_secure=bool(raw.get("cookie_secure", False)) if secure is None else secure == "1",
        ai=AiSettings(**ai_data),
        file_storage_dir=directory.expanduser(),
    )
