"""按实体版本前快照回退目录实体。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import Brand, Bundle, Category, Listing, Sku, SkuMapping, Store

UNDO_UNSUPPORTED = "该实体不支持撤销"


def supports_undo(entity_type: str) -> bool:
    return entity_type in _MODEL


def restore_entity(
    session: Session, entity_type: str, entity_id: str, before: dict[str, Any]
) -> None:
    if not supports_undo(entity_type):
        raise APIError(ErrorCode.VALIDATION_FAILED, UNDO_UNSUPPORTED)
    model = _MODEL[entity_type]
    row: Any = session.get(model, UUID(entity_id))
    if row is None:
        raise APIError(ErrorCode.NOT_FOUND, "撤销目标不存在")
    _FIELDS[entity_type](row, before)
    row.updated_at = datetime.now(UTC)
    row.version = int(row.version) + 1
    session.flush()


def _text(row: Any, before: dict[str, Any], *names: str) -> None:
    for name in names:
        if name in before:
            setattr(row, _snake(name), before[name])


def _store(row: Store, before: dict[str, Any]) -> None:
    _text(row, before, "name", "platform", "marketplace", "currency", "legalEntity")


def _brand(row: Brand, before: dict[str, Any]) -> None:
    _text(row, before, "name", "active")


def _category(row: Category, before: dict[str, Any]) -> None:
    _text(row, before, "name", "active")


def _listing(row: Listing, before: dict[str, Any]) -> None:
    _text(row, before, "status", "asin")


def _sku(row: Sku, before: dict[str, Any]) -> None:
    _text(row, before, "title", "active")


def _mapping(row: SkuMapping, before: dict[str, Any]) -> None:
    _text(row, before, "state", "internalSku")


def _bundle(row: Bundle, before: dict[str, Any]) -> None:
    if "bundleSku" in before:
        row.bundle_sku = before["bundleSku"]
    if "components" in before:
        row.components_json = before["components"]
    if "active" in before:
        row.active = before["active"]


def _snake(name: str) -> str:
    return {
        "internalSku": "internal_sku",
        "bundleSku": "bundle_sku",
        "legalEntity": "legal_entity",
    }.get(name, name)


_MODEL = {
    "Brand": Brand,
    "Category": Category,
    "Listing": Listing,
    "Sku": Sku,
    "SkuMapping": SkuMapping,
    "Bundle": Bundle,
    "Store": Store,
}
_FIELDS: dict[str, Callable[[Any, dict[str, Any]], None]] = {
    "Store": _store,
    "Brand": _brand,
    "Category": _category,
    "Listing": _listing,
    "Sku": _sku,
    "SkuMapping": _mapping,
    "Bundle": _bundle,
}
