"""店铺与当前用户数据范围 JSON API。"""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field, field_validator
from sqlalchemy import select

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import (
    _dispatch_write,
    _page,
    _principal_db,
    _require,
    _write_guard,
)
from crosserp.api.schemas import CamelModel, PageParams
from crosserp.db.schema import Store
from crosserp.iam.scope import apply_store_scope
from crosserp.platform.dispatcher import RiskTier

router = APIRouter()


class StoreCreateRequest(CamelModel):
    platform: str = Field(min_length=1, max_length=32)
    marketplace: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3)
    legal_entity: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class StoreUpdateRequest(CamelModel):
    expected_version: int = Field(alias="expectedVersion", ge=1)
    platform: str | None = Field(default=None, min_length=1, max_length=32)
    marketplace: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    legal_entity: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


def _store_item(row: Store) -> dict[str, object]:
    return {
        "id": str(row.id),
        "platform": row.platform,
        "marketplace": row.marketplace,
        "name": row.name,
        "currency": row.currency,
        "legalEntity": row.legal_entity,
        "version": row.version,
    }


@router.get("/stores")
@api_endpoint(entity="Store", action="Store.list", permission="report:read", risk_tier="none")
def list_stores(
    request: Request, params: Annotated[PageParams, Depends()], q: str | None = Query(None)
) -> dict[str, object]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "report:read", entity="Store")
        statement = apply_store_scope(
            select(Store).order_by(Store.name),
            Store.id,
            request.app.state.permission_service.store_scope(principal, "Store"),
        )
        if q is not None:
            statement = statement.where(Store.name.contains(q))
        rows = list(session.scalars(statement))
        return cast(dict[str, object], _page(params, [_store_item(row) for row in rows], len(rows)))
    finally:
        session.close()


@router.post("/admin/stores", status_code=201)
@api_endpoint(
    entity="Store", action="Store.create", permission="system:write", risk_tier="critical"
)
def create_store(
    request: Request,
    payload: StoreCreateRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, object]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        row = Store(
            id=uuid4(),
            platform=payload.platform,
            marketplace=payload.marketplace,
            name=payload.name,
            currency=payload.currency,
            legal_entity=payload.legal_entity,
            version=1,
        )
        session.add(row)
        _dispatch_write(
            request,
            principal,
            session,
            permission="system:write",
            risk=RiskTier.CRITICAL,
            entity="Store",
            action="Store.create",
            work=lambda: row,
        )
        session.commit()
        return {"id": str(row.id), "status": "created", "version": row.version}
    finally:
        session.close()


@router.patch("/admin/stores/{id}")
@api_endpoint(
    entity="Store", action="Store.update", permission="system:write", risk_tier="critical"
)
def update_store(
    request: Request,
    id: UUID,
    payload: StoreUpdateRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, object]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        row = session.get(Store, id)
        if row is None:
            raise not_found()
        if row.version != payload.expected_version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "店铺版本冲突",
                details={"expectedVersion": payload.expected_version, "version": row.version},
            )

        def work() -> dict[str, object]:
            changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
            for key, value in changes.items():
                setattr(row, key, value)
            row.version += 1
            return {"id": str(row.id), "status": "updated", "version": row.version}

        result = _dispatch_write(
            request,
            principal,
            session,
            permission="system:write",
            risk=RiskTier.CRITICAL,
            entity="Store",
            action="Store.update",
            work=work,
        )
        session.commit()
        return cast(dict[str, object], result)
    finally:
        session.close()


@router.get("/me/data-scope")
@api_endpoint(
    entity="UserAccount",
    action="UserAccount.read_data_scope",
    permission="user:read",
    risk_tier="none",
)
def data_scope(request: Request) -> dict[str, list[object]]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "user:read", entity="UserAccount")
        scope = request.app.state.permission_service.data_scope_filter(principal, "UserAccount")
        return {"scopes": [scope]}
    finally:
        session.close()


__all__ = ["router"]
