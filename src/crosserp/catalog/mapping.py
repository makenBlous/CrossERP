"""平台 SKU 映射业务动作。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import CamelModel
from crosserp.db.schema import SkuMapping, Store
from crosserp.iam.scope import AllStores
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


class MappingCreateInput(CamelModel):
    """创建 SKU 映射的 JSON 输入。"""

    id: UUID = Field(default_factory=uuid4)
    store_id: UUID
    platform_sku: str = Field(min_length=1, max_length=128)
    internal_sku: str = Field(min_length=1, max_length=128)
    confidence: str = Field(default="medium", min_length=1, max_length=32)
    source: Literal["rule", "ai", "human"] | None = None
    state: Literal["suggested", "confirmed"] | None = None

    model_config = CamelModel.model_config | {"str_strip_whitespace": True}


class MappingConfirmInput(CamelModel):
    """确认 SKU 映射的 JSON 输入。"""

    id: UUID
    expected_version: int | None = Field(default=None, ge=0)
    comment: str | None = None
    reason: str | None = None


def _scope_store_allowed(
    principal: Principal, permission_service: PermissionService, store_id: UUID
) -> bool:
    scope = permission_service.store_scope(principal, "SkuMapping")
    return isinstance(scope, AllStores) or store_id in scope


def mapping_dict(row: SkuMapping) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "platformSku": row.platform_sku,
        "storeId": str(row.store_id),
        "internalSku": row.internal_sku,
        "confidence": row.confidence,
        "source": row.source,
        "state": row.state,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance_json,
    }


def create_mapping(
    session: Session,
    principal: Principal,
    payload: MappingCreateInput,
    *,
    permission_service: PermissionService,
    action_id: str = "SkuMapping.create",
) -> dict[str, Any]:
    store_id = payload.store_id
    platform_sku = payload.platform_sku
    internal_sku = payload.internal_sku
    if session.get(Store, store_id) is None or not _scope_store_allowed(
        principal, permission_service, store_id
    ):
        raise not_found(message="店铺不存在")
    source = payload.source or ("ai" if principal.is_agent else "human")
    confidence = payload.confidence
    mapping_id = payload.id or uuid4()
    now = datetime.now(UTC)
    state = payload.state or ("suggested" if source == "ai" else "confirmed")
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
        **row.provenance_json,
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
