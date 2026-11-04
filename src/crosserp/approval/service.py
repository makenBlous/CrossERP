"""审批单服务。所有状态变化和审计写入同一事务。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from crosserp.approval.state import (
    ApprovalState,
    ConcurrentModification,
    coerce_state,
    transition,
)
from crosserp.audit.log import append
from crosserp.db.schema import Approval

_TARGET_TYPE_MAX: Final = 32
_TARGET_ID_MAX: Final = 128
_ACTOR_MAX: Final = 64
_HASH_LENGTH = 64
ApprovalRef = Approval | UUID


def create(
    session: Session,
    *,
    target_type: str,
    target_id: str,
    requested_by: str,
    payload_hash: str | None = None,
    requested_at: datetime | None = None,
    actor_role: str | None = None,
) -> Approval:
    """创建草稿审批单。调用方负责提交事务。"""
    _require_text("target_type", target_type, _TARGET_TYPE_MAX)
    _require_text("target_id", target_id, _TARGET_ID_MAX)
    _require_text("requested_by", requested_by, _ACTOR_MAX)
    _require_hash(payload_hash)
    now = _utc(requested_at)
    row = Approval(
        target_type=target_type,
        target_id=target_id,
        state=ApprovalState.DRAFT.value,
        payload_hash=payload_hash,
        requested_by=requested_by,
        requested_at=now,
        approver=None,
        decided_at=None,
        comment=None,
        token_hash=None,
        used_at=None,
        version=0,
    )
    session.add(row)
    session.flush()
    append(
        session,
        "user",
        "approval.create",
        row.target_type,
        row.target_id,
        None,
        _audit_after(row),
        actor_role=actor_role,
        approval_id=row.id,
    )
    return row


def submit(
    session: Session,
    approval: ApprovalRef,
    *,
    actor: str | None = None,
    actor_role: str | None = None,
) -> Approval:
    """草稿提交，进入待审批。"""  # noqa: RUF002
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.PENDING)
    _update(
        session,
        row,
        {
            "state": ApprovalState.PENDING.value,
            "comment": None,
        },
    )
    _record_transition(
        session,
        row,
        "approval.submit",
        old,
        actor or row.requested_by,
        actor_role=actor_role,
    )
    return row


def approve(
    session: Session,
    approval: ApprovalRef,
    *,
    approver: str,
    payload_hash: str | None = None,
    decided_at: datetime | None = None,
    actor_role: str | None = None,
) -> str:
    """批准审批单并返回一次性明文 token。"""
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.APPROVED)
    _require_text("approver", approver, _ACTOR_MAX)
    current_hash = payload_hash if payload_hash is not None else row.payload_hash
    _require_hash(current_hash)
    now = _utc(decided_at)
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    _update(
        session,
        row,
        {
            "state": ApprovalState.APPROVED.value,
            "payload_hash": current_hash,
            "approver": approver,
            "decided_at": now,
            "comment": None,
            "token_hash": token_hash,
            "used_at": None,
        },
    )
    _record_transition(
        session,
        row,
        "approval.approve",
        old,
        approver,
        actor_role=actor_role,
        reason=None,
        self_approved=row.requested_by == approver,
    )
    return token


def reject(
    session: Session,
    approval: ApprovalRef,
    *,
    approver: str,
    comment: str,
    decided_at: datetime | None = None,
    actor_role: str | None = None,
) -> Approval:
    """驳回审批单。驳回原因必填。"""
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.REJECTED)
    _require_text("approver", approver, _ACTOR_MAX)
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("驳回必须填写原因")
    if len(comment) > 1000:
        raise ValueError("comment 超过 1000 个字符")
    _update(
        session,
        row,
        {
            "state": ApprovalState.REJECTED.value,
            "approver": approver,
            "decided_at": _utc(decided_at),
            "comment": comment,
            "token_hash": None,
            "used_at": None,
        },
    )
    _record_transition(
        session,
        row,
        "approval.reject",
        old,
        approver,
        actor_role=actor_role,
        reason=comment,
        self_approved=row.requested_by == approver,
    )
    return row


def reopen(
    session: Session,
    approval: ApprovalRef,
    *,
    actor: str,
    actor_role: str | None = None,
) -> Approval:
    """将驳回的审批单重新打开为草稿。"""
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.DRAFT)
    _update(
        session,
        row,
        {
            "state": ApprovalState.DRAFT.value,
            "payload_hash": None,
            "approver": None,
            "decided_at": None,
            "comment": None,
            "token_hash": None,
            "used_at": None,
        },
    )
    _record_transition(session, row, "approval.reopen", old, actor, actor_role=actor_role)
    return row


def invalidate(
    session: Session,
    approval: ApprovalRef,
    *,
    current_payload_hash: str,
    actor: str = "system",
    actor_role: str | None = None,
) -> Approval:
    """因报表内容变化让批准失效，回到待审批并清除旧 token。"""  # noqa: RUF002
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.PENDING)
    _require_hash(current_payload_hash)
    _update(
        session,
        row,
        {
            "state": ApprovalState.PENDING.value,
            "payload_hash": current_payload_hash,
            "approver": None,
            "decided_at": None,
            "comment": None,
            "token_hash": None,
            "used_at": None,
        },
    )
    _record_transition(
        session,
        row,
        "approval.invalidate",
        old,
        actor,
        actor_role=actor_role,
        reason="审批内容哈希发生变化",
    )
    return row


def check_fresh(
    session: Session,
    approval: ApprovalRef,
    current_payload_hash: str,
    *,
    actor: str = "system",
    actor_role: str | None = None,
) -> bool:
    """检查批准时锁定的哈希；内容变化会自动失效并返回 False。"""  # noqa: RUF002
    row = _load(session, approval)
    _require_hash(current_payload_hash)
    if coerce_state(row.state) != ApprovalState.APPROVED:
        return False
    if row.payload_hash == current_payload_hash:
        return True
    invalidate(
        session,
        row,
        current_payload_hash=current_payload_hash,
        actor=actor,
        actor_role=actor_role,
    )
    return False


def mark_exported(
    session: Session,
    approval: ApprovalRef,
    *,
    actor: str = "system",
    actor_role: str | None = None,
) -> Approval:
    """把已批准审批单标成已导出，供 T28 的唯一写出口调用。"""  # noqa: RUF002
    row = _load(session, approval)
    old = _audit_after(row)
    transition(row.state, ApprovalState.EXPORTED)
    _update(session, row, {"state": ApprovalState.EXPORTED.value})
    _record_transition(session, row, "approval.export", old, actor, actor_role=actor_role)
    return row


def hash_token(token: str) -> str:
    """计算 token 哈希，库里不保存 token 明文。"""  # noqa: RUF002
    if not isinstance(token, str) or not token:
        raise ValueError("审批 token 不能为空")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(approval: Approval, token: str) -> bool:
    """恒定时间比较 token，供唯一写出口检查。"""  # noqa: RUF002
    import hmac

    return approval.token_hash is not None and hmac.compare_digest(
        approval.token_hash, hash_token(token)
    )


def _load(session: Session, approval: ApprovalRef) -> Approval:
    row = approval if isinstance(approval, Approval) else session.get(Approval, approval)
    if row is None:
        raise LookupError(f"审批单不存在 {approval}")
    return row


def _update(session: Session, row: Approval, values: dict[str, object]) -> None:
    current_version = row.version
    statement = (
        update(Approval)
        .where(Approval.id == row.id, Approval.version == current_version)
        .values(**values, version=Approval.version + 1)
    )
    result = session.execute(statement)
    rowcount = getattr(result, "rowcount", None)
    if rowcount != 1:
        raise ConcurrentModification(row.id)
    session.refresh(row)


def _record_transition(
    session: Session,
    row: Approval,
    action: str,
    before: dict[str, object],
    actor: str,
    *,
    actor_role: str | None,
    reason: str | None = None,
    self_approved: bool = False,
) -> None:
    _require_text("actor", actor, _ACTOR_MAX)
    append(
        session,
        "user" if actor != "system" else "system",
        action,
        row.target_type,
        row.target_id,
        before,
        _audit_after(row),
        actor_role=actor_role,
        reason=reason,
        approval_id=row.id,
        self_approved=self_approved,
    )


def _audit_after(row: Approval) -> dict[str, object]:
    return {
        "id": str(row.id),
        "target_type": row.target_type,
        "target_id": row.target_id,
        "state": row.state,
        "payload_hash": row.payload_hash,
        "requested_by": row.requested_by,
        "requested_at": row.requested_at,
        "approver": row.approver,
        "decided_at": row.decided_at,
        "comment": row.comment,
        "used_at": row.used_at,
        "version": row.version,
    }


def _require_text(name: str, value: str, limit: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 不能为空")
    if len(value) > limit:
        raise ValueError(f"{name} 超过 {limit} 个字符")


def _require_hash(value: str | None) -> None:
    if value is None:
        return
    if len(value) != _HASH_LENGTH or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("payload_hash 必须是 64 位小写十六进制哈希")


def _utc(value: datetime | None) -> datetime:
    result = datetime.now(UTC) if value is None else value
    if result.tzinfo is None or result.tzinfo.utcoffset(result) is None:
        raise ValueError("时间必须带时区")
    return result.astimezone(UTC)
