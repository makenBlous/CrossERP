"""已落库结算的只读查询。解析仍由连接器完成。"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from crosserp.db.schema import Fee, Settlement, SettlementLine, Store

_SORT_COLUMNS = {
    "periodStart": Settlement.period_start,
    "periodEnd": Settlement.period_end,
    "depositDate": Settlement.deposit_date,
    "externalId": Settlement.external_id,
    "platform": Settlement.platform,
    "netPayout": Settlement.total,
}


def query_settlements(
    session: Session,
    *,
    store_ids: list[UUID] | None,
    q: str | None,
    sort_field: str,
    descending: bool,
    page: int,
    page_size: int,
) -> tuple[list[tuple[Settlement, str]], int]:
    """按店铺范围、关键字和排序分页读取结算头。"""
    if store_ids is not None and not store_ids:
        return [], 0
    statement = _filtered(store_ids, q)
    total = cast(int, session.scalar(select(func.count()).select_from(statement.subquery())))
    column: Any = _SORT_COLUMNS[sort_field]
    direction = column.desc() if descending else column.asc()
    tie = Settlement.id.desc() if descending else Settlement.id.asc()
    rows = cast(
        list[tuple[Settlement, str]],
        session.execute(
            statement.order_by(direction, tie).offset((page - 1) * page_size).limit(page_size)
        ).all(),
    )
    return rows, total


def get_settlement_row(
    session: Session,
    settlement_id: UUID,
    store_ids: list[UUID] | None,
) -> tuple[Settlement, str] | None:
    """读取范围内的结算头。范围外与不存在都返回 None。"""
    if store_ids is not None and not store_ids:
        return None
    statement = _filtered(store_ids, None).where(Settlement.id == settlement_id)
    row = cast(
        tuple[Settlement, str] | None,
        session.execute(statement).one_or_none(),
    )
    if row is None:
        return None
    return row


def list_settlement_lines(session: Session, settlement_id: UUID) -> list[SettlementLine]:
    return list(
        session.scalars(
            select(SettlementLine)
            .where(SettlementLine.settlement_id == settlement_id)
            .order_by(SettlementLine.posted_at.asc(), SettlementLine.id.asc())
        )
    )


def list_settlement_fees(session: Session, settlement_id: UUID) -> list[Fee]:
    return list(
        session.scalars(
            select(Fee)
            .join(SettlementLine, SettlementLine.id == Fee.settlement_line_id)
            .where(SettlementLine.settlement_id == settlement_id)
            .order_by(Fee.fee_category.asc(), Fee.id.asc())
        )
    )


def _filtered(store_ids: list[UUID] | None, q: str | None) -> Select[Settlement, str]:
    statement = select(Settlement, Store.name).join(Store, Store.id == Settlement.store_id)
    if store_ids is not None:
        statement = statement.where(Settlement.store_id.in_(store_ids))
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Settlement.external_id.ilike(pattern),
                Settlement.platform.ilike(pattern),
                Store.name.ilike(pattern),
            )
        )
    return statement
