"""审计链检查点。只写锚点，不删除日志。"""  # noqa: RUF002

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.log import AUDIT_LOG_CHAIN, append
from crosserp.db.schema import AuditCheckpoint, AuditHead


def create_checkpoint(session: Session, *, reason: str) -> AuditCheckpoint:
    """记录当前链尾检查点。"""
    if not reason.strip():
        raise ValueError("检查点必须填写 reason")
    if len(reason) > 512:
        raise ValueError("reason 超过 512 个字符")
    head = session.scalar(select(AuditHead).where(AuditHead.chain == AUDIT_LOG_CHAIN))
    row = AuditCheckpoint(
        id=uuid4(),
        chain=AUDIT_LOG_CHAIN,
        upto_id=None if head is None else head.last_id,
        upto_hash="0" * 64 if head is None or head.last_hash is None else head.last_hash,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    append(
        session,
        "system",
        "audit.checkpoint",
        "audit_checkpoint",
        str(row.id),
        None,
        {"upto_hash": row.upto_hash, "reason": reason},
        reason=reason,
        self_approved=False,
    )
    return row
