"""security_event 独立追加哈希链。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.audit.chain import GENESIS_PREV_HASH, compute_hash, json_ready
from crosserp.db.dialects import lock_for_update
from crosserp.db.schema import AuditHead, SecurityEvent


class SecurityEventName(StrEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    USER_CREATED = "user_created"
    USER_DISABLED = "user_disabled"
    USER_ENABLED = "user_enabled"
    ROLE_GRANTED = "role_granted"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_DENIED = "permission_denied"
    SESSION_EXPIRED = "session_expired"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"


def record(
    session: Session,
    event: SecurityEventName | str,
    *,
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    target_user_id: uuid.UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    detail: Any = None,
    ts: datetime | None = None,
) -> SecurityEvent:
    event_name = event.value if isinstance(event, SecurityEventName) else event
    if event_name not in {item.value for item in SecurityEventName}:
        raise ValueError(f"不认识的安全事件: {event_name}")
    head = _head(session)
    previous = head.last_hash or GENESIS_PREV_HASH
    current = session.scalar(select(func.max(SecurityEvent.seq)))
    row = SecurityEvent(
        id=uuid.uuid4(),
        seq=int(current or 0) + 1,
        ts=ts or datetime.now(UTC),
        event=event_name,
        user_id=user_id,
        username=username[:64] if username else None,
        target_user_id=target_user_id,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
        detail_json=None if detail is None else json_ready(detail),
        prev_hash=previous,
        hash=GENESIS_PREV_HASH,
    )
    session.add(row)
    session.flush()
    row.hash = compute_hash(row.prev_hash, _payload(row))
    head.last_id = row.id
    head.last_hash = row.hash
    session.flush()
    return row


def verify_security_chain(session: Session) -> bool:
    rows = list(
        session.scalars(select(SecurityEvent).order_by(SecurityEvent.seq, SecurityEvent.id))
    )
    head = session.scalar(select(AuditHead).where(AuditHead.chain == "security"))
    previous = GENESIS_PREV_HASH
    for index, row in enumerate(rows, start=1):
        if (
            row.seq != index
            or row.prev_hash != previous
            or row.hash != compute_hash(row.prev_hash, _payload(row))
        ):
            return False
        previous = row.hash
    return (not rows and (head is None or head.last_hash is None)) or (
        head is not None and head.last_id == rows[-1].id and head.last_hash == rows[-1].hash
    )


def _head(session: Session) -> AuditHead:
    statement = lock_for_update(session, select(AuditHead).where(AuditHead.chain == "security"))
    head = session.scalar(statement)
    if head is not None:
        return head
    head = AuditHead(id=uuid.uuid4(), chain="security", last_id=None, last_hash=None)
    session.add(head)
    session.flush()
    return head


def _payload(row: SecurityEvent) -> dict[str, object]:
    return {
        "id": str(row.id),
        "seq": row.seq,
        "ts": row.ts.isoformat(),
        "event": row.event,
        "user_id": str(row.user_id) if row.user_id else None,
        "username": row.username,
        "target_user_id": str(row.target_user_id) if row.target_user_id else None,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "request_id": row.request_id,
        "detail_json": row.detail_json,
        "prev_hash": row.prev_hash,
    }
