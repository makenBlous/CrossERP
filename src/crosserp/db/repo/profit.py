"""Profit snapshot persistence."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import ProfitSnapshot


def get_snapshot(
    session: Session,
    *,
    store_id: UUID,
    period: str,
    internal_sku: str,
    calc_version: str,
    inputs_hash: str,
) -> ProfitSnapshot | None:
    return session.scalar(
        select(ProfitSnapshot).where(
            ProfitSnapshot.store_id == store_id,
            ProfitSnapshot.period == period,
            ProfitSnapshot.internal_sku == internal_sku,
            ProfitSnapshot.calc_version == calc_version,
            ProfitSnapshot.inputs_hash == inputs_hash,
        )
    )


def insert_snapshot(session: Session, **values: object) -> ProfitSnapshot:
    row = ProfitSnapshot(id=uuid4(), **values)
    session.add(row)
    session.flush()
    return row
