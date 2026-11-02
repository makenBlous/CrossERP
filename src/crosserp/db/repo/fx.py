"""月汇率读写样例。"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.dialects import upsert
from crosserp.db.schema import FxRate


def get_fx_rate(session: Session, period: str, from_ccy: str, to_ccy: str) -> FxRate | None:
    """按期间和币种对读取汇率。"""
    statement = select(FxRate).where(
        FxRate.period == period,
        FxRate.from_ccy == from_ccy,
        FxRate.to_ccy == to_ccy,
    )
    return session.scalars(statement).one_or_none()


def upsert_fx_rate(
    session: Session,
    *,
    rate_id: UUID,
    period: str,
    from_ccy: str,
    to_ccy: str,
    rate: Decimal,
    source: str,
) -> None:
    """按 period + from_ccy + to_ccy 插入或更新汇率。冲突时保留原主键。"""
    upsert(
        session,
        FxRate.__table__,
        {
            "id": rate_id,
            "period": period,
            "from_ccy": from_ccy,
            "to_ccy": to_ccy,
            "rate": rate,
            "source": source,
        },
        ["period", "from_ccy", "to_ccy"],
        ["rate", "source"],
    )
