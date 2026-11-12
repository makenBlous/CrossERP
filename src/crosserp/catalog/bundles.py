"""组合装实体的确定性读写。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import Bundle, Sku
from crosserp.iam.scope import AllStores, apply_store_scope
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


def normalize_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for component in components:
        internal_sku = str(component["internalSku"])
        quantity = Decimal(str(component["qty"]))
        if not internal_sku or quantity <= 0:
            raise APIError(ErrorCode.VALIDATION_FAILED, "组合装组成和数量无效")
        qty: int | str = (
            int(quantity) if quantity == quantity.to_integral_value() else format(quantity, "f")
        )
        normalized.append({"internalSku": internal_sku, "qty": qty})
    return normalized


def get_bundle(session: Session, bundle_id: UUID) -> Bundle:
    row = session.get(Bundle, bundle_id)
    if row is None:
        raise not_found(message="组合装不存在")
    return row


def create_bundle(
    session: Session,
    *,
    bundle_id: UUID,
    bundle_sku: str,
    components: list[dict[str, Any]],
    principal: Principal,
) -> Bundle:
    existing = session.scalar(select(Bundle).where(Bundle.bundle_sku == bundle_sku))
    if existing is not None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "组合 SKU 已存在")
    now = datetime.now(UTC)
    row = Bundle(
        id=bundle_id,
        bundle_sku=bundle_sku,
        components_json=normalize_components(components),
        active=True,
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
    return row


def update_bundle(
    session: Session,
    row: Bundle,
    *,
    bundle_sku: str | None,
    components: list[dict[str, Any]] | None,
    principal: Principal,
) -> tuple[dict[str, Any], dict[str, Any]]:
    before = bundle_payload(row)
    if bundle_sku is not None and bundle_sku != row.bundle_sku:
        duplicate = session.scalar(
            select(Bundle).where(Bundle.bundle_sku == bundle_sku, Bundle.id != row.id)
        )
        if duplicate is not None:
            raise APIError(ErrorCode.VALIDATION_FAILED, "组合 SKU 已存在")
        row.bundle_sku = bundle_sku
    if components is not None:
        row.components_json = normalize_components(components)
    row.version += 1
    row.updated_at = datetime.now(UTC)
    row.provenance_json = {
        "actorType": "agent" if principal.is_agent else "human",
        "actorId": str(principal.user_id) if principal.user_id else None,
        "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
    }
    session.flush()
    return before, bundle_payload(row)


def deactivate_bundle(session: Session, row: Bundle) -> tuple[dict[str, Any], dict[str, Any]]:
    before = bundle_payload(row)
    row.active = False
    row.version += 1
    row.updated_at = datetime.now(UTC)
    session.flush()
    return before, bundle_payload(row)


def bundle_in_store_scope(
    session: Session,
    row: Bundle,
    principal: Principal,
    permission_service: PermissionService,
) -> bool:
    """组合装没有店铺列。可见性由组成 SKU 所在店铺决定。"""
    scope = permission_service.store_scope(principal, "Bundle")
    if isinstance(scope, AllStores):
        return True
    skus = [str(item["internalSku"]) for item in row.components_json]
    if not skus:
        return False
    allowed = set(
        session.scalars(
            apply_store_scope(
                select(Sku.internal_sku).where(Sku.internal_sku.in_(skus)),
                Sku.store_id,
                scope,
            )
        )
    )
    return set(skus) <= allowed


def bundle_payload(row: Bundle) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "bundleSku": row.bundle_sku,
        "components": row.components_json,
        "active": row.active,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


__all__ = [
    "bundle_in_store_scope",
    "bundle_payload",
    "create_bundle",
    "deactivate_bundle",
    "get_bundle",
    "normalize_components",
    "update_bundle",
]
