"""商品类目树的查询与实体动作。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import Field, StrictInt, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import CamelModel
from crosserp.db.schema import Category
from crosserp.platform.dispatcher import ActionDispatcher
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal


class CategoryCreatePayload(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name 必须是 1-255 个字符")
        return normalized


class CategoryUpdatePayload(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None
    expected_version: StrictInt | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name 必须是 1-255 个字符")
        return normalized

    @model_validator(mode="after")
    def reject_explicit_null_name(self) -> CategoryUpdatePayload:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name 必须是 1-255 个字符")
        return self


class CategoryStatusPayload(CamelModel):
    id: UUID
    status: Literal["active", "inactive"]
    expected_version: StrictInt | None = Field(default=None, ge=1)


def list_categories(
    session: Session,
    *,
    principal: Principal,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
) -> dict[str, Any]:
    DefaultPermissionService().require(principal, "item_group:read")
    statement = select(Category)
    if q:
        statement = statement.where(Category.name.ilike(f"%{q}%"))
    total = cast(int, session.scalar(select(func.count()).select_from(statement.subquery())))
    if sort is None:
        ordering: tuple[Any, ...] = (Category.name.asc(), Category.id.asc())
    else:
        descending = sort.startswith("-")
        field = sort[1:] if descending else sort
        if field == "name":
            column: Any = func.lower(Category.name)
        elif field == "createdAt":
            column = Category.created_at
        else:
            raise APIError(ErrorCode.VALIDATION_FAILED, "sort 只支持 name 或 createdAt")
        ordering = (
            column.desc() if descending else column.asc(),
            Category.id.desc() if descending else Category.id.asc(),
        )
    rows = list(
        session.scalars(
            statement.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return {
        "items": [_as_dict(row) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def create_category(
    session: Session,
    *,
    principal: Principal,
    payload: CategoryCreatePayload,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    name = payload.name
    parent_id = payload.parent_id
    if parent_id is not None:
        parent = session.get(Category, parent_id)
        if parent is None:
            raise not_found(message="父类目不存在")
    category_id = uuid4()
    payload_data = payload.model_dump(by_alias=True, mode="json", exclude_unset=True)

    def business_action() -> dict[str, Any]:
        now = datetime.now(UTC)
        row = Category(
            id=category_id,
            name=name,
            parent_id=parent_id,
            active=True,
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        result = _as_dict(row)
        result["undo"] = {
            "action": "Category.delete",
            "entity": "Category",
            "id": str(category_id),
            "previous": None,
        }
        return result

    return cast(
        dict[str, Any],
        ActionDispatcher(session=session).dispatch(
            principal=principal,
            permission="item_group:create",
            risk_tier="medium",
            action="Category.create",
            entity="Category",
            entity_id=category_id,
            payload=payload_data,
            idempotency_key=idempotency_key,
            request_id=request_id,
            business_action=business_action,
        ),
    )


def update_category(
    session: Session,
    *,
    principal: Principal,
    category_id: UUID,
    payload: CategoryUpdatePayload,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    expected_version = payload.expected_version
    payload_data = payload.model_dump(by_alias=True, mode="json", exclude_unset=True)

    def business_action() -> dict[str, Any]:
        row = session.get(Category, category_id)
        if row is None:
            raise not_found(message="类目不存在")
        if expected_version is None:
            raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是正整数")
        name = payload.name if "name" in payload.model_fields_set else None
        parent_id = payload.parent_id if "parent_id" in payload.model_fields_set else None
        before = _as_dict(row)
        if name is not None:
            row.name = name
        if "parent_id" in payload.model_fields_set:
            if parent_id is not None:
                parent = session.get(Category, parent_id)
                if parent is None:
                    raise not_found(message="父类目不存在")
                if parent_id == category_id or _contains_descendant(session, category_id, parent):
                    raise APIError(ErrorCode.ILLEGAL_TRANSITION, "类目树不能成环", status_code=409)
            row.parent_id = parent_id
        row.version += 1
        row.updated_at = datetime.now(UTC)
        session.flush()
        result = _as_dict(row)
        result["before"] = before
        result["after"] = _as_dict(row)
        result["diff"] = {"before": before, "after": result["after"]}
        result["undo"] = {
            "action": "Category.update",
            "entity": "Category",
            "id": str(category_id),
            "previous": before,
        }
        return result

    return cast(
        dict[str, Any],
        ActionDispatcher(session=session).dispatch(
            principal=principal,
            permission="item_group:write",
            risk_tier="medium",
            action="Category.update",
            entity="Category",
            entity_id=category_id,
            payload=payload_data,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            business_action=business_action,
        ),
    )


def set_category_status(
    session: Session,
    *,
    principal: Principal,
    category_id: UUID,
    payload: CategoryStatusPayload,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    expected_version = payload.expected_version
    payload_data = payload.model_dump(by_alias=True, mode="json", exclude_unset=True)

    def business_action() -> dict[str, Any]:
        row = session.get(Category, category_id)
        if row is None:
            raise not_found(message="类目不存在")
        if expected_version is None:
            raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是正整数")
        status = payload.status
        active = status == "active"
        before = _as_dict(row)
        row.active = active
        row.version += 1
        row.updated_at = datetime.now(UTC)
        session.flush()
        result = _as_dict(row)
        result["before"] = before
        result["after"] = _as_dict(row)
        result["diff"] = {"before": before, "after": result["after"]}
        result["undo"] = {
            "action": "Category.status",
            "entity": "Category",
            "id": str(category_id),
            "previous": before["active"],
        }
        return result

    return cast(
        dict[str, Any],
        ActionDispatcher(session=session).dispatch(
            principal=principal,
            permission="item_group:write",
            risk_tier="medium",
            action="Category.status",
            entity="Category",
            entity_id=category_id,
            payload=payload_data,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            business_action=business_action,
        ),
    )


def _as_dict(row: Category) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "parentId": str(row.parent_id) if row.parent_id else None,
        "active": row.active,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def _contains_descendant(session: Session, category_id: UUID, parent: Category) -> bool:
    current: Category | None = parent
    while current is not None:
        if current.id == category_id:
            return True
        current = session.get(Category, current.parent_id) if current.parent_id else None
    return False


__all__ = [
    "CategoryCreatePayload",
    "CategoryStatusPayload",
    "CategoryUpdatePayload",
    "create_category",
    "list_categories",
    "set_category_status",
    "update_category",
]
