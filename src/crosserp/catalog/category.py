"""商品类目树的查询与实体动作。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import Category
from crosserp.platform.dispatcher import ActionDispatcher
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal


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
    rows = list(session.scalars(select(Category).order_by(Category.name, Category.id)))
    if q:
        needle = q.casefold()
        rows = [row for row in rows if needle in row.name.casefold()]
    rows = _sort(rows, sort)
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": [_as_dict(row) for row in rows[start : start + page_size]],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def create_category(
    session: Session,
    *,
    principal: Principal,
    payload: dict[str, Any],
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    _ensure_keys(payload, {"name", "parentId"})
    name = _text(payload, "name")
    parent_id = _optional_uuid(payload, "parentId")
    if parent_id is not None and session.get(Category, parent_id) is None:
        raise not_found(message="父类目不存在")
    category_id = uuid4()

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
            payload=payload,
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
    payload: dict[str, Any],
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    raw_expected_version = payload.get("expectedVersion")
    expected_version = raw_expected_version if _is_version(raw_expected_version) else None

    def business_action() -> dict[str, Any]:
        row = session.get(Category, category_id)
        if row is None:
            raise not_found(message="类目不存在")
        _ensure_keys(payload, {"name", "parentId", "expectedVersion"})
        _required_version(payload)
        name = _text(payload, "name") if "name" in payload else None
        parent_id = _optional_uuid(payload, "parentId") if "parentId" in payload else None
        before = _as_dict(row)
        if name is not None:
            row.name = name
        if "parentId" in payload:
            if parent_id is not None and session.get(Category, parent_id) is None:
                raise not_found(message="父类目不存在")
            if parent_id == category_id or _contains_descendant(session, category_id, parent_id):
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
            payload=payload,
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
    payload: dict[str, Any],
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    raw_expected_version = payload.get("expectedVersion")
    expected_version = raw_expected_version if _is_version(raw_expected_version) else None

    def business_action() -> dict[str, Any]:
        row = session.get(Category, category_id)
        if row is None:
            raise not_found(message="类目不存在")
        _ensure_keys(payload, {"id", "status", "expectedVersion"})
        _required_version(payload)
        status = payload.get("status")
        if status not in {"active", "inactive"}:
            raise APIError(ErrorCode.VALIDATION_FAILED, "status 必须是 active 或 inactive")
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
            payload=payload,
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


def _sort(rows: list[Category], sort: str | None) -> list[Category]:
    if sort is None:
        return rows
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field == "name":
        return sorted(rows, key=lambda row: row.name.casefold(), reverse=descending)
    if field == "createdAt":
        return sorted(rows, key=lambda row: row.created_at, reverse=descending)
    raise APIError(ErrorCode.VALIDATION_FAILED, "sort 只支持 name 或 createdAt")


def _ensure_keys(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise APIError(
            ErrorCode.VALIDATION_FAILED, "请求包含未知字段", details={"fields": sorted(unknown)}
        )


def _text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{key} 必须是 1-255 个字符")
    return value.strip()


def _optional_uuid(payload: dict[str, Any], key: str) -> UUID | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{key} 必须是 UUID")
    try:
        return UUID(value)
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{key} 必须是 UUID") from exc


def _required_version(payload: dict[str, Any]) -> int:
    value = payload.get("expectedVersion")
    if not _is_version(value):
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是正整数")
    return cast(int, value)


def _is_version(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _contains_descendant(session: Session, category_id: UUID, parent_id: UUID | None) -> bool:
    current = parent_id
    while current is not None:
        if current == category_id:
            return True
        row = session.get(Category, current)
        current = None if row is None else row.parent_id
    return False


__all__ = ["create_category", "list_categories", "set_category_status", "update_category"]
