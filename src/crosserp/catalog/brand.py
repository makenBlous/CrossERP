"""品牌主数据动作。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import Brand
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import Principal


def brand_dict(row: Brand) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "active": row.active,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance or {},
    }


class BrandService:
    """品牌查询与动作服务。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, page: int, page_size: int, q: str | None, sort: str | None) -> dict[str, Any]:
        statement = select(Brand)
        if q:
            statement = statement.where(Brand.name.ilike(f"%{q}%"))
        sort_name = (sort or "name").lstrip("-")
        if sort_name != "name":
            raise APIError(ErrorCode.VALIDATION_FAILED, "品牌只支持按 name 排序")
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

    def get(self, brand_id: str) -> Brand:
        try:
            parsed = UUID(brand_id)
        except ValueError as exc:
            raise not_found(message="品牌不存在") from exc
        row = self.session.get(Brand, parsed)
        if row is None:
            raise not_found(message="品牌不存在")
        return row

    def create(
        self,
        *,
        principal: Principal,
        payload: Mapping[str, Any],
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        name = _name(payload)
        brand_id = uuid4()

        def business() -> dict[str, Any]:
            now = datetime.now(UTC)
            row = Brand(
                id=brand_id,
                name=name,
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
                "after": after,
                "undo": {
                    "action": "Brand.status",
                    "payload": {"id": str(brand_id), "status": "inactive", "expectedVersion": 1},
                },
            }

        return self._dispatch(
            principal=principal,
            action="Brand.create",
            permission="brand:create",
            entity_id=brand_id,
            payload=dict(payload),
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
        payload: Mapping[str, Any],
        expected_version: int | None,
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        parsed_id = _parse_id(brand_id)
        self.get(brand_id)
        self.session.commit()
        name = _name(payload)

        def business() -> dict[str, Any]:
            row = self.session.get(Brand, parsed_id)
            if row is None:
                raise not_found(message="品牌不存在")
            before = brand_dict(row)
            row.name = name
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
            payload=dict(payload),
            expected_version=expected_version,
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
        active: bool,
        expected_version: int | None,
        payload: Mapping[str, Any],
        idempotency_key: str | None,
        request_id: str | None,
        tool_call_id: str | None,
    ) -> dict[str, Any]:
        parsed_id = _parse_id(brand_id)
        self.get(brand_id)
        self.session.commit()

        def business() -> dict[str, Any]:
            row = self.session.get(Brand, parsed_id)
            if row is None:
                raise not_found(message="品牌不存在")
            before = brand_dict(row)
            row.active = active
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
                        "status": "active" if before["active"] else "inactive",
                    },
                },
            }

        return self._dispatch(
            principal=principal,
            action="Brand.status",
            permission="brand:write",
            entity_id=parsed_id,
            payload=dict(payload),
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            tool_call_id=tool_call_id,
            business_action=business,
        )

    def _dispatch(self, **kwargs: Any) -> dict[str, Any]:
        with self.session.begin():
            result = ActionDispatcher(session=self.session).dispatch(
                risk_tier=RiskTier.MEDIUM, **kwargs
            )
        return cast(dict[str, Any], result)


def _parse_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise not_found(message="品牌不存在") from exc


def _name(payload: Mapping[str, Any]) -> str:
    value = payload.get("name")
    if not isinstance(value, str) or not value.strip():
        raise APIError(ErrorCode.VALIDATION_FAILED, "品牌名称不能为空")
    return value.strip()


__all__ = ["BrandService", "brand_dict"]
