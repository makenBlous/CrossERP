"""SKU 主档查询与动作实现。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from crosserp.api.errors import not_found
from crosserp.db.schema import Brand, Category, EntityVersion, Sku, SkuCost, Store
from crosserp.platform.permissions import DefaultPermissionService, PermissionService
from crosserp.platform.principal import Principal


def page_values(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def list_skus(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
    permission_service: PermissionService | None = None,
) -> dict[str, Any]:
    statement = select(Sku)
    statement = _apply_store_scope(
        statement, principal, permission_service or DefaultPermissionService(), Sku.store_id
    )
    if q:
        pattern = f"%{q}%"
        statement = statement.where(or_(Sku.internal_sku.like(pattern), Sku.title.like(pattern)))
    rows = list(session.scalars(statement))
    _sort_rows(rows, sort)
    return page_values(
        [sku_dict(row, include_cost=False, session=session) for row in rows], page, page_size
    )


def get_sku(
    session: Session,
    principal: Principal,
    sku_id: UUID,
    *,
    permission_service: PermissionService | None = None,
) -> dict[str, Any]:
    statement = select(Sku).where(Sku.id == sku_id)
    statement = _apply_store_scope(
        statement, principal, permission_service or DefaultPermissionService(), Sku.store_id
    )
    row = session.scalar(statement)
    if row is None:
        raise not_found(message="SKU 不存在")
    include_cost = _can_read_cost(principal)
    return sku_dict(row, include_cost=include_cost, session=session)


def create_sku(session: Session, payload: Mapping[str, Any]) -> tuple[UUID, dict[str, Any]]:
    now = datetime.now(UTC)
    sku_id = UUID(str(payload.get("id", uuid4())))
    row = Sku(
        id=sku_id,
        store_id=_uuid_or_none(payload.get("storeId")),
        platform_sku=str(payload.get("platformSku", payload["internalSku"])),
        internal_sku=str(payload["internalSku"]),
        title=str(payload["title"]),
        title_en=_string_or_none(payload.get("titleEn")),
        brand_id=_uuid_or_none(payload.get("brandId")),
        category_id=_uuid_or_none(payload.get("categoryId")),
        uom=_string_or_none(payload.get("uom")),
        weight_kg=payload.get("weightKg"),
        hs_code=_string_or_none(payload.get("hsCode")),
        aliases_json=payload.get("aliases", []),
        active=bool(payload.get("active", False)),
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
    principal: Principal, store_id: UUID | None, service: PermissionService | None = None
) -> None:
    scope = (service or DefaultPermissionService()).data_scope_filter(principal, "Sku")
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
    permission_service: PermissionService | None = None,
) -> dict[str, Any]:
    service = permission_service or DefaultPermissionService()
    rows: list[dict[str, Any]] = []
    categories = list(session.scalars(select(Category).where(Category.active.is_(True))))
    brands = list(session.scalars(select(Brand).where(Brand.active.is_(True))))
    stores_statement = select(Store)
    stores_statement = _apply_store_scope(stores_statement, principal, service, Store.id)
    stores = list(session.scalars(stores_statement))
    for category in categories:
        rows.append(
            {
                "kind": "category",
                "id": str(category.id),
                "label": category.name,
                "value": str(category.id),
            }
        )
    for brand in brands:
        rows.append(
            {"kind": "brand", "id": str(brand.id), "label": brand.name, "value": str(brand.id)}
        )
    for store in stores:
        rows.append(
            {"kind": "store", "id": str(store.id), "label": store.name, "value": str(store.id)}
        )
    currencies = sorted({"CNY", "USD", "EUR", "GBP", "JPY"} | {row.currency for row in stores})
    for currency in currencies:
        rows.append({"kind": "currency", "id": currency, "label": currency, "value": currency})
    if q:
        folded = q.casefold()
        rows = [row for row in rows if folded in f"{row['label']}{row['value']}".casefold()]
    if sort and sort.lstrip("-") in {"kind", "label", "value"}:
        rows.sort(key=lambda row: row[sort.lstrip("-")], reverse=sort.startswith("-"))
    return page_values(rows, page, page_size)


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
        "aliases": row.aliases_json or [],
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


def _sort_rows(rows: list[Sku], sort: str | None) -> None:
    if sort and sort.lstrip("-") in {"internalSku", "title", "active"}:
        field = sort.lstrip("-")
        rows.sort(key=lambda row: getattr(row, _snake(field)), reverse=sort.startswith("-"))


def _can_read_cost(principal: Principal) -> bool:
    return bool(
        {"item:cost:read", "cost:read"} & principal.permissions
        or {"admin", "finance"} & principal.roles
    )


def _snake(name: str) -> str:
    return {"internalSku": "internal_sku"}.get(name, name)


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
