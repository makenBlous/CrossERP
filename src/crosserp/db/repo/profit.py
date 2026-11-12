"""Profit snapshot persistence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from crosserp.db.schema import ProfitSnapshot, Sku, Store


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


_SORT_COLUMNS = {
    "internalSku": ProfitSnapshot.internal_sku,
    "period": ProfitSnapshot.period,
    "storeName": Store.name,
    "revenue": ProfitSnapshot.revenue,
    "profit": ProfitSnapshot.profit,
    "status": ProfitSnapshot.status,
}


def _ordering(sort: str | None) -> tuple[Any, ...]:
    if sort is None:
        return (
            Store.name.asc(),
            ProfitSnapshot.internal_sku.asc(),
            ProfitSnapshot.period.asc(),
            ProfitSnapshot.id.asc(),
        )
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    column = _SORT_COLUMNS[field]
    return (
        column.desc() if descending else column.asc(),
        ProfitSnapshot.id.desc() if descending else ProfitSnapshot.id.asc(),
    )


def list_snapshots(
    session: Session,
    *,
    store_ids: Sequence[UUID] | None,
    store_id: UUID | None,
    period: str | None,
    internal_sku: str | None,
    q: str | None,
    sort: str | None,
    offset: int,
    limit: int | None,
) -> tuple[list[tuple[ProfitSnapshot, Store, str | None]], int]:
    """返回已保存的利润快照。store_ids 为空序列时没有可见店铺。"""
    if store_ids is not None and not store_ids:
        return [], 0
    name = (
        select(func.min(Sku.title))
        .where(
            Sku.store_id == ProfitSnapshot.store_id,
            Sku.internal_sku == ProfitSnapshot.internal_sku,
        )
        .scalar_subquery()
    )
    statement = select(ProfitSnapshot, Store, name).join(Store, Store.id == ProfitSnapshot.store_id)
    if store_ids is not None:
        statement = statement.where(ProfitSnapshot.store_id.in_(tuple(store_ids)))
    if store_id is not None:
        statement = statement.where(ProfitSnapshot.store_id == store_id)
    if period is not None:
        statement = statement.where(ProfitSnapshot.period == period)
    if internal_sku is not None:
        statement = statement.where(ProfitSnapshot.internal_sku == internal_sku)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(ProfitSnapshot.internal_sku.ilike(pattern), Store.name.ilike(pattern))
        )
    total = cast(int, session.scalar(select(func.count()).select_from(statement.subquery())))
    ordered = statement.order_by(*_ordering(sort))
    if limit is not None:
        ordered = ordered.offset(offset).limit(limit)
    rows = [(snapshot, store, title) for snapshot, store, title in session.execute(ordered)]
    return rows, total


def insert_snapshot(session: Session, **values: object) -> ProfitSnapshot:
    row = ProfitSnapshot(id=uuid4(), **values)
    session.add(row)
    session.flush()
    return row
