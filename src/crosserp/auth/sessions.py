"""服务器端登录会话。cookie 只携带明文 token, 数据库只保存哈希。"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import AppUser, UserSession


@dataclass(frozen=True)
class SessionToken:
    value: str
    csrf_token: str
    expires_at: datetime


def create_session(
    session: Session,
    user: AppUser,
    *,
    ip: str | None,
    user_agent: str | None,
    hours: int,
    now: datetime | None = None,
) -> SessionToken:
    moment = now or datetime.now(UTC)
    value = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    row = UserSession(
        id=_digest(value),
        user_id=user.id,
        created_at=moment,
        expires_at=moment + timedelta(hours=hours),
        last_seen_at=moment,
        ip=ip,
        user_agent=user_agent,
        csrf_token_hash=_digest(csrf),
        revoked_at=None,
    )
    session.add(row)
    session.flush()
    return SessionToken(value, csrf, row.expires_at)


def find_user(
    session: Session, token: str | None, *, now: datetime | None = None
) -> AppUser | None:
    if not token:
        return None
    row = session.scalar(select(UserSession).where(UserSession.id == _digest(token)))
    moment = now or datetime.now(UTC)
    if row is None or row.revoked_at is not None or row.expires_at <= moment:
        return None
    user = session.get(AppUser, row.user_id)
    if user is None or not user.is_active:
        return None
    row.last_seen_at = moment
    return user


def revoke_session(session: Session, token: str | None, *, now: datetime | None = None) -> None:
    if not token:
        return
    row = session.scalar(select(UserSession).where(UserSession.id == _digest(token)))
    if row is not None and row.revoked_at is None:
        row.revoked_at = now or datetime.now(UTC)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
