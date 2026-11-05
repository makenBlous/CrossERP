"""个人 API token 的创建、校验和吊销。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.db.schema import ApiToken, AppUser


def create_token(
    session: Session, user: AppUser, *, name: str, days: int = 90
) -> tuple[ApiToken, str]:
    plain = "cerp_" + secrets.token_urlsafe(32)
    row = ApiToken(
        id=UUID(bytes=secrets.token_bytes(16)),
        user_id=user.id,
        name=name,
        token_hash=hashlib.sha256(plain.encode()).hexdigest(),
        scopes=["ai.ask"],
        created_at=datetime.now(UTC),
        last_used_at=None,
        revoked_at=None,
    )
    session.add(row)
    session.flush()
    record_security(
        session,
        SecurityEventName.TOKEN_CREATED,
        user_id=user.id,
        username=user.username,
        detail={"token_id": str(row.id), "name": name},
    )
    return row, plain


def authenticate(session: Session, plain: str) -> tuple[ApiToken, AppUser] | None:
    digest = hashlib.sha256(plain.encode()).hexdigest()
    row = session.scalar(
        select(ApiToken).where(ApiToken.token_hash == digest, ApiToken.revoked_at.is_(None))
    )
    if row is None or (row.created_at + timedelta(days=90)) <= datetime.now(UTC):
        return None
    user = session.get(AppUser, row.user_id)
    if user is None or not user.is_active:
        return None
    row.last_used_at = datetime.now(UTC)
    return row, user


def revoke_token(session: Session, token_id: UUID, user: AppUser) -> bool:
    row = session.get(ApiToken, token_id)
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.now(UTC)
    record_security(
        session,
        SecurityEventName.TOKEN_REVOKED,
        user_id=user.id,
        username=user.username,
        detail={"token_id": str(token_id)},
    )
    return True
