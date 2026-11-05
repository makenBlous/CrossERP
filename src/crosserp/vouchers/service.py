"""凭证草稿保存、平衡校验和来源去重。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.audit.log import append
from crosserp.db.schema import Voucher, VoucherLine
from crosserp.vouchers.model import VoucherDraft


def save_draft(session: Session, draft: VoucherDraft) -> Voucher:
    """保存一张平衡凭证。void 之外的同来源凭证只能有一张。"""
    draft.validate_balance()
    existing = session.scalar(
        select(Voucher).where(
            Voucher.store_id == draft.store_id,
            Voucher.period == draft.period,
            Voucher.source_type == draft.source_type,
            Voucher.source_id == draft.source_id,
            Voucher.state != "void",
        )
    )
    if existing is not None:
        raise ValueError("同一来源已有未作废凭证, 请先作废后再生成")
    row = Voucher(
        id=draft.id or uuid4(),
        store_id=draft.store_id,
        period=draft.period,
        source_type=draft.source_type,
        source_id=draft.source_id,
        state="draft",
        currency=draft.currency,
        total_debit=draft.total_debit,
        total_credit=draft.total_credit,
        inputs_hash=draft.inputs_hash,
        accounts_hash=draft.accounts_hash,
        created_by=draft.created_by,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    for line in draft.lines:
        session.add(
            VoucherLine(
                id=uuid4(),
                voucher_id=row.id,
                line_no=line.line_no,
                account_key=line.account_key,
                account_code=line.account_code,
                account_name=line.account_name,
                debit=line.debit,
                credit=line.credit,
                summary=line.summary,
                source_ref=line.source_ref,
            )
        )
    session.flush()
    append(
        session,
        "user",
        "voucher.create",
        "voucher",
        str(row.id),
        None,
        {"state": row.state, "total_debit": row.total_debit, "total_credit": row.total_credit},
        actor_name=draft.created_by,
    )
    return row


def voucher_payload(row: Voucher, session: Session) -> str:
    """计算审批锁定的凭证内容哈希, 包含科目哈希和每条分录。"""
    lines = list(
        session.scalars(
            select(VoucherLine)
            .where(VoucherLine.voucher_id == row.id)
            .order_by(VoucherLine.line_no)
        )
    )
    import hashlib
    import json

    value = {
        "inputs_hash": row.inputs_hash,
        "accounts_hash": row.accounts_hash,
        "lines": [
            {
                "line_no": line.line_no,
                "account_key": line.account_key,
                "account_code": line.account_code,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "source_ref": line.source_ref,
            }
            for line in lines
        ],
    }
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
