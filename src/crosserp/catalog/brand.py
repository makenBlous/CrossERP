"""品牌主数据动作。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import not_found
from crosserp.api.schemas import BrandCreateRequest, BrandStatusRequest, BrandUpdateRequest
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.db.schema import Brand
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


def brand_dict(row: Brand) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "active": row.active,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance,
    }


class BrandService:
    """品牌查询与动作服务。"""

    def __init__(self, session: Session, permission_service: PermissionService) -> None:
        self.session = session
        self.permission_service = permission_service

    def list(
        self,
        *,
        principal: Principal,
        page: int,
        page_size: int,
        q: str | None,
        sort: str | None,
    ) -> dict[str, Any]:
        self.permission_service.require(principal, "brand:read")
        statement = select(Brand)
        if q:
            statement = statement.where(Brand.name.ilike(f"%{q}%"))
        ordering = Brand.name.desc() if (sort or "").startswith("-") else Brand.name.asc()
        total = int(
            self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = list(
            self.session.scalars(
                statement.order_by(ordering, Brand.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {
            "items": [brand_dict(row) for row in rows],
            "page": page,
            "pageSize": page_size,
            "total": total,
        }

    def create(
        self,
        *,
        principal: Principal,
        payload: BrandCreateRequest,
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        brand_id = uuid4()

        def business() -> dict[str, Any]:
            now = datetime.now(UTC)
            row = Brand(
                id=brand_id,
                name=payload.name,
                active=True,
                version=1,
                created_at=now,
                updated_at=now,
                provenance={"actorType": "agent" if principal.is_agent else "human"},
            )
            self.session.add(row)
            self.session.flush()
            after = brand_dict(row)
            return {
                "id": str(brand_id),
                "status": "succeeded",
                "before": {},
                "after": after,
                "undo": {
                    "action": "Brand.status",
                    "payload": {"ids": [str(brand_id)], "active": False, "expectedVersion": 1},
                },
            }

        return self._dispatch(
            principal=principal,
            action="Brand.create",
            permission="brand:create",
            entity_id=brand_id,
            payload=payload.model_dump(by_alias=True),
            idempotency_key=idempotency_key,
            request_id=request_id,
            tool_call_id=tool_call_id,
            business_action=business,
        )

    def update(
        self,
        *,
        principal: Principal,
        brand_id: str,
        payload: BrandUpdateRequest,
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        parsed_id = _parse_id(brand_id)

        def business() -> dict[str, Any]:
            row = self.session.get(Brand, parsed_id)
            if row is None:
                raise not_found(message="品牌不存在")
            before = brand_dict(row)
            row.name = payload.name
            row.updated_at = datetime.now(UTC)
            row.version += 1
            self.session.flush()
            after = brand_dict(row)
            return {
                "id": brand_id,
                "status": "succeeded",
                "before": before,
                "after": after,
                "undo": {
                    "action": "Brand.update",
                    "payload": {"id": brand_id, "name": before["name"]},
                },
            }

        return self._dispatch(
            principal=principal,
            action="Brand.update",
            permission="brand:write",
            entity_id=parsed_id,
            payload=payload.model_dump(by_alias=True, exclude_none=True),
            expected_version=payload.expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            tool_call_id=tool_call_id,
            business_action=business,
        )

    def status(
        self,
        *,
        principal: Principal,
        brand_id: str,
        payload: BrandStatusRequest,
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        parsed_id = _parse_id(brand_id)

        def business() -> dict[str, Any]:
            row = self.session.get(Brand, parsed_id)
            if row is None:
                raise not_found(message="品牌不存在")
            before = brand_dict(row)
            row.active = payload.active
            row.updated_at = datetime.now(UTC)
            row.version += 1
            self.session.flush()
            after = brand_dict(row)
            return {
                "id": brand_id,
                "status": "succeeded",
                "before": before,
                "after": after,
                "undo": {
                    "action": "Brand.status",
                    "payload": {
                        "id": brand_id,
                        "active": before["active"],
                    },
                },
            }

        return self._dispatch(
            principal=principal,
            action="Brand.status",
            permission="brand:write",
            entity_id=parsed_id,
            payload=payload.model_dump(by_alias=True, exclude_none=True),
            expected_version=payload.expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            tool_call_id=tool_call_id,
            business_action=business,
        )

    def _dispatch(self, **kwargs: Any) -> dict[str, Any]:
        result = make_action_dispatcher(
            self.session, self.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(risk_tier=RiskTier.MEDIUM, **kwargs)
        return cast(dict[str, Any], result)


def _parse_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise not_found(message="品牌不存在") from exc


__all__ = ["BrandService", "brand_dict"]
