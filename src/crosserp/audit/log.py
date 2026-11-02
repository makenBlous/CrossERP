"""只追加审计。不提供修改或删除。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.chain import GENESIS_HASH, compute_hash, to_jsonable
from crosserp.db.schema import AuditHead, AuditLog

BUSINESS_CHAIN = "business"
_OPTIONAL = frozenset(
    {
        "actor_user_id",
        "actor_role",
        "approval_id",
        "approver_id",
        "reason",
        "request_id",
        "ip",
        "user_agent",
        "self_approved",
    }
)


@dataclass(frozen=True)
class VerifyResult:
    """哈希链校验结果。"""

    ok: bool
    checked: int
    first_bad_id: str | None = None
    reason: str | None = None


def append(
    session: Session,
    actor_type: str,
    action: str,
    target_type: str,
    target_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    **optional: object,
) -> AuditLog:
    """在调用方事务里追加一条审计。失败时由调用方回滚。"""
    unknown = set(optional) - _OPTIONAL
    if unknown:
        names = "、".join(sorted(unknown))
        raise TypeError(f"不支持的审计字段 {names}")
    head = _locked_head(session)
    prev_hash = head.last_hash or GENESIS_HASH
    row = AuditLog(
        id=uuid4(),
        ts=datetime.now(UTC),
        actor_type=actor_type,
        actor_user_id=_optional_uuid(optional.get("actor_user_id"), "actor_user_id"),
        actor_role=_optional_str(optional.get("actor_role"), "actor_role"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_json=_json_object(before, "before"),
        after_json=_json_object(after, "after"),
        approval_id=_optional_uuid(optional.get("approval_id"), "approval_id"),
        approver_id=_optional_uuid(optional.get("approver_id"), "approver_id"),
        reason=_optional_str(optional.get("reason"), "reason"),
        request_id=_optional_str(optional.get("request_id"), "request_id"),
        ip=_optional_str(optional.get("ip"), "ip"),
        user_agent=_optional_str(optional.get("user_agent"), "user_agent"),
        self_approved=_optional_bool(optional.get("self_approved"), default=False),
        prev_hash=prev_hash,
        hash=GENESIS_HASH,
    )
    row.hash = compute_hash(prev_hash, _body(row))
    session.add(row)
    head.last_id = row.id
    head.last_hash = row.hash
    session.flush()
    return row


def verify_chain(session: Session) -> VerifyResult:
    """按 prev_hash 重算。中间被改或被删都会失败。"""
    rows = list(session.scalars(select(AuditLog)).all())
    head = _read_head(session)
    if not rows:
        if head is None or (head.last_id is None and head.last_hash is None):
            return VerifyResult(ok=True, checked=0)
        return VerifyResult(ok=False, checked=0, reason="审计链头指向不存在的记录")

    prev = GENESIS_HASH
    seen: set[UUID] = set()
    last: AuditLog | None = None
    while True:
        matches = [row for row in rows if row.prev_hash == prev and row.id not in seen]
        if not matches:
            break
        if len(matches) > 1:
            return VerifyResult(
                ok=False,
                checked=len(seen),
                first_bad_id=str(matches[0].id),
                reason="哈希链分叉",
            )
        row = matches[0]
        expected = compute_hash(prev, _body(row))
        if row.hash != expected:
            return VerifyResult(
                ok=False,
                checked=len(seen),
                first_bad_id=str(row.id),
                reason="哈希不一致",
            )
        seen.add(row.id)
        prev = row.hash
        last = row
    if len(seen) != len(rows):
        missing = next(row for row in rows if row.id not in seen)
        return VerifyResult(
            ok=False,
            checked=len(seen),
            first_bad_id=str(missing.id),
            reason="哈希链中断或存在游离记录",
        )
    if head is None or last is None or head.last_id != last.id or head.last_hash != last.hash:
        return VerifyResult(
            ok=False,
            checked=len(seen),
            first_bad_id=None if last is None else str(last.id),
            reason="审计链头与最后一条不一致",
        )
    return VerifyResult(ok=True, checked=len(seen))


def _body(row: AuditLog) -> dict[str, object]:
    return {
        "id": str(row.id),
        "ts": row.ts,
        "actor_type": row.actor_type,
        "actor_user_id": None if row.actor_user_id is None else str(row.actor_user_id),
        "actor_role": row.actor_role,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "before_json": row.before_json,
        "after_json": row.after_json,
        "approval_id": None if row.approval_id is None else str(row.approval_id),
        "approver_id": None if row.approver_id is None else str(row.approver_id),
        "reason": row.reason,
        "request_id": row.request_id,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "self_approved": row.self_approved,
        "prev_hash": row.prev_hash,
    }


def _locked_head(session: Session) -> AuditHead:
    head = _read_head(session, lock=True)
    if head is not None:
        return head
    head = AuditHead(chain=BUSINESS_CHAIN, last_id=None, last_hash=None)
    session.add(head)
    session.flush()
    locked = _read_head(session, lock=True)
    if locked is None:
        raise RuntimeError("审计链头写入后读不到")
    return locked


def _read_head(session: Session, *, lock: bool = False) -> AuditHead | None:
    statement = select(AuditHead).where(AuditHead.chain == BUSINESS_CHAIN)
    if lock and session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    return session.scalars(statement).one_or_none()


def _json_object(value: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    ready = to_jsonable(value)
    if not isinstance(ready, dict):
        raise TypeError(f"{name} 必须是对象或空")
    return cast(dict[str, Any], ready)


def _optional_uuid(value: object, name: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    raise TypeError(f"{name} 必须是 UUID 或空")


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise TypeError(f"{name} 必须是字符串或空")


def _optional_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError("self_approved 必须是布尔值")
