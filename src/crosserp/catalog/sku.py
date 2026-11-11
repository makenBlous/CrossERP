"""SKU 主档查询与动作实现。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from typing import cast as typing_cast
from uuid import UUID

from sqlalchemy import String, func, literal, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.orm import Session

from crosserp.api.errors import not_found
from crosserp.db.schema import Brand, Category, EntityVersion, Sku, SkuCost, Store
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


def list_skus(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
    permission_service: PermissionService,
) -> dict[str, Any]:
    statement = select(Sku)
    statement = _apply_store_scope(statement, principal, permission_service, Sku.store_id)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(or_(Sku.internal_sku.like(pattern), Sku.title.like(pattern)))
    sort_field = _SKU_SORT_FIELDS[sort.lstrip("-")] if sort else Sku.internal_sku
    ordering = sort_field.desc() if sort and sort.startswith("-") else sort_field.asc()
    statement = statement.order_by(ordering, Sku.id).offset((page - 1) * page_size).limit(page_size)
    total = typing_cast(
        int, session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    )
    rows = session.scalars(statement).all()
    return {
        "items": [sku_dict(row, include_cost=False, session=session) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": int(total),
    }


def get_sku(
    session: Session,
    principal: Principal,
    sku_id: UUID,
    *,
    permission_service: PermissionService,
) -> dict[str, Any]:
    statement = select(Sku).where(Sku.id == sku_id)
    statement = _apply_store_scope(statement, principal, permission_service, Sku.store_id)
    row = session.scalar(statement)
    if row is None:
        raise not_found(message="SKU 不存在")
    include_cost = _can_read_cost(principal)
    return sku_dict(row, include_cost=include_cost, session=session)


def create_sku(
    session: Session, payload: Mapping[str, Any], *, sku_id: UUID
) -> tuple[UUID, dict[str, Any]]:
    now = datetime.now(UTC)
    row = Sku(
        id=sku_id,
        store_id=_uuid_or_none(payload.get("storeId")),
        platform_sku=str(payload["platformSku"]),
        internal_sku=str(payload["internalSku"]),
        title=str(payload["title"]),
        title_en=_string_or_none(payload.get("titleEn")),
        brand_id=_uuid_or_none(payload.get("brandId")),
        category_id=_uuid_or_none(payload.get("categoryId")),
        uom=_string_or_none(payload.get("uom")),
        weight_kg=payload.get("weightKg"),
        hs_code=_string_or_none(payload.get("hsCode")),
        aliases_json=payload["aliases"],
        active=bool(payload["active"]),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    result = {
        "id": str(row.id),
        "status": "succeeded",
        "after": sku_dict(row, include_cost=False),
        "undo": {"action": "Sku.update", "payload": {"id": str(row.id), "active": False}},
    }
    return row.id, result


def ensure_store_allowed(
    principal: Principal, store_id: UUID | None, service: PermissionService
) -> None:
    scope = service.data_scope_filter(principal, "Sku")
    values = scope.get("storeIds") or scope.get("store_ids")
    if values and (store_id is None or str(store_id) not in {str(value) for value in values}):
        raise not_found(message="SKU 不存在")


def update_sku(session: Session, sku_id: UUID, payload: Mapping[str, Any]) -> dict[str, Any]:
    row = session.get(Sku, sku_id)
    if row is None:
        raise not_found(message="SKU 不存在")
    before = sku_dict(row, include_cost=False)
    field_map = {
        "storeId": "store_id",
        "platformSku": "platform_sku",
        "internalSku": "internal_sku",
        "title": "title",
        "titleEn": "title_en",
        "brandId": "brand_id",
        "categoryId": "category_id",
        "uom": "uom",
        "weightKg": "weight_kg",
        "hsCode": "hs_code",
        "aliases": "aliases_json",
        "active": "active",
    }
    for key, attr in field_map.items():
        if key in payload:
            value = payload[key]
            if key.endswith("Id") or key == "storeId":
                value = _uuid_or_none(value)
            setattr(row, attr, value)
    row.updated_at = datetime.now(UTC)
    session.flush()
    after = sku_dict(row, include_cost=False)
    return {
        "id": str(row.id),
        "status": "succeeded",
        "before": before,
        "after": after,
        "undo": {"action": "Sku.update", "payload": before},
    }


def change_status(session: Session, sku_id: UUID, active: bool) -> dict[str, Any]:
    row = session.get(Sku, sku_id)
    if row is None:
        raise not_found(message="SKU 不存在")
    before = sku_dict(row, include_cost=False)
    row.active = active
    row.updated_at = datetime.now(UTC)
    session.flush()
    return {
        "id": str(row.id),
        "status": "succeeded",
        "before": before,
        "after": sku_dict(row, include_cost=False),
        "undo": {"action": "Sku.status", "payload": {"ids": [str(row.id)], "active": not active}},
    }


def list_lookups(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
    permission_service: PermissionService,
) -> dict[str, Any]:
    stores_statement = _apply_store_scope(select(Store), principal, permission_service, Store.id)
    stores: Any = stores_statement.subquery("scoped_store")
    category_rows = select(
        literal("category").label("kind"),
        sa_cast(Category.__table__.c.id, String(36)).label("id"),
        Category.__table__.c.name.label("label"),
        sa_cast(Category.__table__.c.id, String(36)).label("value"),
    ).where(Category.active.is_(True))
    brand_rows = select(
        literal("brand").label("kind"),
        sa_cast(Brand.__table__.c.id, String(36)).label("id"),
        Brand.__table__.c.name.label("label"),
        sa_cast(Brand.__table__.c.id, String(36)).label("value"),
    ).where(Brand.active.is_(True))
    store_rows = select(
        literal("store").label("kind"),
        sa_cast(stores.c.id, String(36)).label("id"),
        stores.c.name.label("label"),
        sa_cast(stores.c.id, String(36)).label("value"),
    )
    currency_rows = select(
        literal("currency").label("kind"),
        stores.c.currency.label("id"),
        stores.c.currency.label("label"),
        stores.c.currency.label("value"),
    ).distinct()
    lookup_rows = category_rows.union_all(brand_rows, store_rows, currency_rows).subquery("lookups")
    statement = select(lookup_rows)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                lookup_rows.c.kind.like(pattern),
                lookup_rows.c.label.like(pattern),
                lookup_rows.c.value.like(pattern),
            )
        )
    sort_field = (
        lookup_rows.c[_LOOKUP_SORT_FIELDS[sort.lstrip("-")]] if sort else lookup_rows.c.kind
    )
    ordering = sort_field.desc() if sort and sort.startswith("-") else sort_field.asc()
    statement = statement.order_by(ordering, lookup_rows.c.id)
    total = typing_cast(
        int, session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    )
    rows = (
        session.execute(statement.offset((page - 1) * page_size).limit(page_size)).mappings().all()
    )
    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": int(total),
    }


def sku_dict(row: Sku, *, include_cost: bool, session: Session | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row.id),
        "internalSku": row.internal_sku,
        "platformSku": row.platform_sku,
        "title": row.title,
        "titleEn": row.title_en,
        "storeId": str(row.store_id) if row.store_id else None,
        "brandId": str(row.brand_id) if row.brand_id else None,
        "categoryId": str(row.category_id) if row.category_id else None,
        "uom": row.uom,
        "weightKg": str(row.weight_kg) if row.weight_kg is not None else None,
        "hsCode": row.hs_code,
        "aliases": row.aliases_json,
        "active": row.active,
        "version": 0
        if session is None
        else int(
            session.scalar(
                select(func.max(EntityVersion.version)).where(
                    EntityVersion.entity_type == "Sku", EntityVersion.entity_id == str(row.id)
                )
            )
            or 0
        ),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_cost and session is not None:
        cost = session.scalar(
            select(SkuCost)
            .where(SkuCost.internal_sku == row.internal_sku)
            .order_by(SkuCost.valid_from.desc())
        )
        if cost is not None:
            result["unitCost"] = _money(cost.unit_cost, cost.currency)
            result["freightPerUnit"] = _money(cost.freight_per_unit, cost.currency)
    return result


def _money(value: Decimal, currency: str) -> dict[str, Any]:
    return {"amountMinor": int(value * 10000), "currency": currency}


def _apply_store_scope(
    statement: Any, principal: Principal, service: PermissionService, column: Any
) -> Any:
    scope = service.data_scope_filter(principal, "Sku")
    values = scope.get("storeIds") or scope.get("store_ids")
    if values:
        statement = statement.where(column.in_([UUID(str(value)) for value in values]))
    return statement


def _can_read_cost(principal: Principal) -> bool:
    return bool(
        {"item:cost:read", "cost:read"} & principal.permissions
        or {"admin", "finance"} & principal.roles
    )


def _uuid_or_none(value: Any) -> UUID | None:
    return None if value in (None, "") else UUID(str(value))


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


__all__ = [
    "change_status",
    "create_sku",
    "ensure_store_allowed",
    "get_sku",
    "list_lookups",
    "list_skus",
    "sku_dict",
    "update_sku",
]


_SKU_SORT_FIELDS = {
    "internalSku": Sku.internal_sku,
    "title": Sku.title,
    "active": Sku.active,
}

_LOOKUP_SORT_FIELDS = {
    "kind": "kind",
    "label": "label",
    "value": "value",
}
