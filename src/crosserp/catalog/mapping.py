"""平台 SKU 映射业务动作。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import SkuMapping, Store
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


def _scope_store_allowed(
    principal: Principal, permission_service: PermissionService, store_id: UUID
) -> bool:
    scope = permission_service.data_scope_filter(principal, "SkuMapping")
    if not scope:
        return True
    allowed = scope.get("storeIds", scope.get("storeId"))
    if allowed is None:
        return True
    values = allowed if isinstance(allowed, (list, tuple, set, frozenset)) else [allowed]
    return str(store_id) in {str(value) for value in values}


def mapping_dict(row: SkuMapping) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "platformSku": row.platform_sku,
        "storeId": str(row.store_id),
        "internalSku": row.internal_sku,
        "confidence": row.confidence,
        "source": row.source,
        "state": row.state,
        "status": row.state,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance_json,
    }


def parse_uuid(value: Any, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{field} 必须是 UUID") from exc


def create_mapping(
    session: Session,
    principal: Principal,
    payload: dict[str, Any],
    *,
    permission_service: PermissionService,
    action_id: str = "SkuMapping.create",
) -> dict[str, Any]:
    store_id = parse_uuid(payload.get("storeId"), "storeId")
    platform_sku = str(payload.get("platformSku", "")).strip()
    internal_sku = str(payload.get("internalSku", "")).strip()
    if not platform_sku or not internal_sku:
        raise APIError(ErrorCode.VALIDATION_FAILED, "platformSku 和 internalSku 不能为空")
    if session.get(Store, store_id) is None or not _scope_store_allowed(
        principal, permission_service, store_id
    ):
        raise not_found(message="店铺不存在")
    source = str(payload.get("source") or ("ai" if principal.is_agent else "human"))
    if source not in {"rule", "ai", "human"}:
        raise APIError(ErrorCode.VALIDATION_FAILED, "source 必须是 rule、ai 或 human")
    confidence = str(payload.get("confidence") or "medium")
    mapping_id = parse_uuid(payload["id"], "id") if payload.get("id") else uuid4()
    now = datetime.now(UTC)
    requested_state = payload.get("state", payload.get("status"))
    state = requested_state if requested_state in {"suggested", "confirmed"} else None
    if state is None:
        state = "suggested" if source == "ai" else "confirmed"
    provenance = {
        "actionId": action_id,
        "actorType": "agent" if principal.is_agent else "human",
        "actorId": str(principal.user_id) if principal.user_id else None,
        "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
    }
    row = SkuMapping(
        id=mapping_id,
        store_id=store_id,
        platform_sku=platform_sku,
        internal_sku=internal_sku,
        confidence=confidence,
        source=source,
        state=state,
        version=1,
        created_at=now,
        updated_at=now,
        provenance_json=provenance,
    )
    session.add(row)
    session.flush()
    result = mapping_dict(row)
    result["undoPayload"] = {"action": "SkuMapping.delete", "id": str(mapping_id)}
    return result


def confirm_mapping(
    session: Session,
    principal: Principal,
    mapping_id: UUID,
    *,
    permission_service: PermissionService,
    expected_version: int | None,
) -> dict[str, Any]:
    row = session.get(SkuMapping, mapping_id)
    if row is None or not _scope_store_allowed(principal, permission_service, row.store_id):
        raise not_found(message="映射不存在")
    if expected_version is not None and expected_version != row.version:
        raise APIError(
            ErrorCode.CONFLICT_VERSION,
            "实体版本已变化",
            details={"expectedVersion": expected_version, "actualVersion": row.version},
        )
    before = mapping_dict(row)
    row.state = "confirmed"
    row.version += 1
    row.updated_at = datetime.now(UTC)
    row.provenance_json = {
        **(row.provenance_json or {}),
        "actionId": "SkuMapping.confirm",
        "actorType": "agent" if principal.is_agent else "human",
        "actorId": str(principal.user_id) if principal.user_id else None,
        "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
    }
    session.flush()
    result = mapping_dict(row)
    result["before"] = before
    result["after"] = mapping_dict(row)
    return result
