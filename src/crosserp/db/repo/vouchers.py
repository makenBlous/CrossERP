"""凭证表的数据库访问。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Voucher, VoucherLine


def get_voucher(session: Session, voucher_id: UUID) -> Voucher | None:
    return session.get(Voucher, voucher_id)


def list_vouchers(session: Session) -> list[Voucher]:
    return list(session.scalars(select(Voucher).order_by(Voucher.created_at, Voucher.id)))


def list_lines(session: Session, voucher_id: UUID) -> list[VoucherLine]:
    return list(
        session.scalars(
            select(VoucherLine)
            .where(VoucherLine.voucher_id == voucher_id)
            .order_by(VoucherLine.line_no)
        )
    )
