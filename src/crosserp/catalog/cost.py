"""SKU 成本期间业务服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import EntityEvent, SkuCost
from crosserp.platform.principal import Principal


def period_bounds(period: str) -> tuple[datetime, datetime]:
    year, month = (int(part) for part in period.split("-"))
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return start, end


def list_costs(
    session: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
) -> tuple[list[SkuCost], int]:
    statement = select(SkuCost)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(SkuCost.internal_sku.ilike(pattern), SkuCost.period.ilike(pattern))
        )
    total_statement = select(SkuCost.id)
    if q:
        total_statement = total_statement.where(
            or_(SkuCost.internal_sku.ilike(pattern), SkuCost.period.ilike(pattern))
        )
    total = session.query(total_statement.subquery()).count()
    sort_value = sort or "-period"
    sort_name = sort_value.lstrip("-")
    sort_column = {
        "period": SkuCost.period,
        "internalSku": SkuCost.internal_sku,
        "createdAt": SkuCost.created_at,
        "updatedAt": SkuCost.updated_at,
    }.get(sort_name)
    if sort_column is None:
        raise APIError(ErrorCode.VALIDATION_ERROR, "sort 字段不支持")
    statement = statement.order_by(
        sort_column.desc() if sort_value.startswith("-") else sort_column
    )
    rows = list(session.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return rows, int(total)


def create_cost(
    session: Session,
    *,
    entity_id: UUID,
    internal_sku: str,
    period: str,
    amount_minor: int,
    currency: str,
    source: str,
    principal: Principal,
) -> dict[str, Any]:
    valid_from, valid_to = period_bounds(period)
    statement = select(SkuCost).where(SkuCost.internal_sku == internal_sku)
    for existing in session.scalars(statement):
        existing_from = existing.valid_from
        existing_to = existing.valid_to
        if existing.period:
            existing_from, existing_to = period_bounds(existing.period)
        if existing_to is None or (valid_from < existing_to and existing_from < valid_to):
            raise APIError(
                ErrorCode.VALIDATION_ERROR,
                "同一 SKU 的成本期间不能重叠",
                details={"internalSku": internal_sku, "period": period},
            )
    amount = Decimal(amount_minor) / Decimal(10000)
    now = datetime.now(UTC)
    row = SkuCost(
        id=entity_id,
        internal_sku=internal_sku,
        valid_from=valid_from,
        valid_to=valid_to,
        unit_cost=amount,
        currency=currency,
        freight_per_unit=Decimal("0.0000"),
        period=period,
        source=source,
        status="effective",
        version=1,
        created_at=now,
        updated_at=now,
        provenance_json={
            "actorType": "agent" if principal.is_agent else "human",
            "actorId": str(principal.user_id) if principal.user_id else None,
            "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
        },
    )
    session.add(row)
    session.flush()
    session.add(
        EntityEvent(
            id=uuid4(),
            event_type="profit.recompute_required",
            entity_type="SkuCost",
            entity_id=str(entity_id),
            action_id="SkuCost.create",
            payload_json={
                "notificationKind": "profit_recompute_required",
                "internalSku": internal_sku,
                "period": period,
            },
            created_at=now,
        )
    )
    return serialize_cost(row)


def serialize_cost(row: SkuCost) -> dict[str, Any]:
    period = row.period or row.valid_from.astimezone(UTC).strftime("%Y-%m")
    return {
        "id": str(row.id),
        "internalSku": row.internal_sku,
        "period": period,
        "unitCost": {
            "amountMinor": int(row.unit_cost * Decimal(10000)),
            "currency": row.currency,
        },
        "source": row.source,
        "status": row.status,
        "version": row.version,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "provenance": row.provenance_json,
    }


__all__ = ["create_cost", "list_costs", "period_bounds", "serialize_cost"]
