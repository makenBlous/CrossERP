"""只追加审计哈希链。不提供修改或删除。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.audit.chain import GENESIS_PREV_HASH, compute_hash, json_ready
from crosserp.db.dialects import lock_for_update
from crosserp.db.schema import AuditHead, AuditLog

AUDIT_LOG_CHAIN = "audit_log"
_ACTOR_TYPES = frozenset({"user", "agent", "system"})
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
        "ts",
    }
)
_LIMITS = {
    "actor_type": 32,
    "actor_role": 32,
    "action": 64,
    "target_type": 64,
    "target_id": 64,
    "reason": 512,
    "request_id": 64,
    "ip": 64,
    "user_agent": 512,
}


@dataclass(frozen=True)
class VerifyResult:
    """哈希链校验结果。checked 是已通过的条数。失败时不含坏记录。"""

    ok: bool
    checked: int
    first_bad_id: str | None
    reason: str | None


def append(
    session: Session,
    actor_type: str,
    action: str,
    target_type: str,
    target_id: str,
    before: object,
    after: object,
    **optional: object,
) -> AuditLog:
    """在调用方的事务里追加一条审计。不提交。写失败则调用方一起回滚。"""
    unknown = set(optional) - _OPTIONAL
    if unknown:
        raise TypeError(f"未知参数: {', '.join(sorted(unknown))}")
    _require_actor(actor_type)
    _require_text("action", action, required=True)
    _require_text("target_type", target_type, required=True)
    _require_text("target_id", target_id, required=True)
    _require_text("actor_role", _optional_text("actor_role", optional))
    _require_text("reason", _optional_text("reason", optional))
    _require_text("request_id", _optional_text("request_id", optional))
    _require_text("ip", _optional_text("ip", optional))
    _require_text("user_agent", _optional_text("user_agent", optional))

    head = _locked_head(session)
    previous = head.last_hash or GENESIS_PREV_HASH
    current = session.scalar(select(func.max(AuditLog.seq)))
    next_seq = int(current or 0) + 1
    row = AuditLog(
        id=uuid.uuid4(),
        seq=next_seq,
        ts=_require_ts(optional.get("ts")),
        actor_type=actor_type,
        actor_user_id=_optional_uuid("actor_user_id", optional),
        actor_role=_optional_text("actor_role", optional),
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_json=_stored_json(before),
        after_json=_stored_json(after),
        approval_id=_optional_uuid("approval_id", optional),
        approver_id=_optional_uuid("approver_id", optional),
        reason=_optional_text("reason", optional),
        request_id=_optional_text("request_id", optional),
        ip=_optional_text("ip", optional),
        user_agent=_optional_text("user_agent", optional),
        self_approved=_require_bool(optional.get("self_approved", False)),
        prev_hash=previous,
        hash=GENESIS_PREV_HASH,
    )
    session.add(row)
    session.flush()
    # 先写入再读回。哈希按数据库读出的值计算。避免时间精度在三库上不一致。
    session.refresh(row)
    digest = compute_hash(row.prev_hash, payload_from_log(row))
    row.hash = digest
    head.last_id = row.id
    head.last_hash = digest
    session.flush()
    return row


def verify_chain(session: Session) -> VerifyResult:
    """按 seq 重算哈希链。空链且链头为空时通过。"""
    rows = list(session.scalars(select(AuditLog).order_by(AuditLog.seq, AuditLog.id)))
    head = session.scalar(select(AuditHead).where(AuditHead.chain == AUDIT_LOG_CHAIN))
    if not rows:
        if head is not None and (head.last_id is not None or head.last_hash is not None):
            bad = str(head.last_id) if head.last_id is not None else None
            return VerifyResult(False, 0, bad, "审计记录已空但链头仍有指针")
        return VerifyResult(True, 0, None, None)

    previous = GENESIS_PREV_HASH
    for index, row in enumerate(rows, start=1):
        row_id = str(row.id)
        if row.seq != index:
            return VerifyResult(
                False,
                index - 1,
                row_id,
                f"序号不连续。期望 {index} 实际 {row.seq}",
            )
        if row.prev_hash != previous:
            return VerifyResult(False, index - 1, row_id, "prev_hash 与上一条不一致")
        try:
            expected = compute_hash(row.prev_hash, payload_from_log(row))
        except (TypeError, ValueError) as exc:
            return VerifyResult(False, index - 1, row_id, f"记录无法规范化: {exc}")
        if row.hash != expected:
            return VerifyResult(False, index - 1, row_id, "哈希与记录内容不一致")
        previous = row.hash

    if head is None or head.last_id != rows[-1].id or head.last_hash != rows[-1].hash:
        bad = str(rows[-1].id)
        if head is not None and head.last_id is not None:
            bad = str(head.last_id)
        return VerifyResult(False, len(rows), bad, "audit_head 与链尾不一致")
    return VerifyResult(True, len(rows), None, None)


def payload_from_log(row: AuditLog) -> dict[str, object]:
    """除 hash 以外的全部列。校验和写入用同一份。"""
    return {
        "id": _uuid_text(row.id),
        "seq": row.seq,
        "ts": _iso_from_row(row.ts),
        "actor_type": row.actor_type,
        "actor_user_id": _uuid_text(row.actor_user_id),
        "actor_role": row.actor_role,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "before_json": row.before_json,
        "after_json": row.after_json,
        "approval_id": _uuid_text(row.approval_id),
        "approver_id": _uuid_text(row.approver_id),
        "reason": row.reason,
        "request_id": row.request_id,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "self_approved": _as_bool(row.self_approved),
        "prev_hash": row.prev_hash,
    }


def _locked_head(session: Session) -> AuditHead:
    statement = lock_for_update(
        session,
        select(AuditHead).where(AuditHead.chain == AUDIT_LOG_CHAIN),
    )
    head = session.scalars(statement).one_or_none()
    if head is not None:
        return head
    # 不在这里开 SAVEPOINT。SQLite 驱动可能把 SAVEPOINT 提前提交。
    # 并发首次建链头时唯一约束失败。整个事务回滚。
    created = AuditHead(id=uuid.uuid4(), chain=AUDIT_LOG_CHAIN, last_id=None, last_hash=None)
    session.add(created)
    session.flush()
    return created


def _stored_json(value: object) -> object:
    if value is None:
        return None
    return json_ready(value)


def _require_actor(actor_type: str) -> None:
    _require_text("actor_type", actor_type, required=True)
    if actor_type not in _ACTOR_TYPES:
        raise ValueError("actor_type 必须是 user、agent 或 system")


def _require_text(name: str, value: str | None, *, required: bool = False) -> None:
    if value is None:
        if required:
            raise ValueError(f"{name} 不能为空")
        return
    if not isinstance(value, str):
        raise TypeError(f"{name} 必须是字符串")
    if required and not value:
        raise ValueError(f"{name} 不能为空")
    limit = _LIMITS[name]
    if len(value) > limit:
        raise ValueError(f"{name} 超过 {limit} 个字符")


def _optional_text(name: str, optional: dict[str, object]) -> str | None:
    if name not in optional or optional[name] is None:
        return None
    value = optional[name]
    if not isinstance(value, str):
        raise TypeError(f"{name} 必须是字符串")
    return value


def _optional_uuid(name: str, optional: dict[str, object]) -> uuid.UUID | None:
    if name not in optional or optional[name] is None:
        return None
    value = optional[name]
    if not isinstance(value, uuid.UUID):
        raise TypeError(f"{name} 必须是 UUID")
    return value


def _require_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError("self_approved 必须是布尔值")
    return value


def _require_ts(value: object) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if not isinstance(value, datetime):
        raise TypeError("ts 必须是 datetime")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("时间必须带时区")
    return value


def _uuid_text(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(uuid.UUID(value))


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value in {0, 1}:
        return bool(value)
    raise TypeError("self_approved 必须是布尔值")


def _iso_from_row(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="microseconds")
