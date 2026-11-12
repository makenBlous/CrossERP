"""SKU 成本期间 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field, field_validator
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import CamelModel, Money
from crosserp.catalog.cost import create_cost, list_costs, serialize_cost
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["商品与主数据"])


class CostCreate(CamelModel):
    internal_sku: str = Field(alias="internalSku", min_length=1, max_length=128)
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    unit_cost: Money = Field(alias="unitCost")
    source: Literal["purchase", "landed", "manual"] = "manual"
    expected_version: int | None = Field(default=None, alias="expectedVersion", ge=0)

    @field_validator("unit_cost")
    @classmethod
    def uppercase_currency(cls, value: Money) -> Money:
        if value.currency != value.currency.upper():
            raise ValueError("currency 必须是大写 ISO 代码")
        return value


def _require(principal: Principal, permission: str, service: PermissionService) -> None:
    service.require(principal, permission)


@router.get("/catalog/costs")
@api_endpoint(
    entity="SkuCost",
    action="SkuCost.list",
    permission="item:read",
    risk_tier="none",
    idempotency="none",
)
def get_costs(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, object]:
    _require(principal, "item:read", permission_service)
    with Session(request.app.state.database_engine) as session:
        rows, total = list_costs(
            session,
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
            principal=principal,
            permission_service=permission_service,
        )
    return {
        "items": [serialize_cost(row) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.post("/catalog/costs", status_code=201)
@api_endpoint(
    entity="SkuCost",
    action="SkuCost.create",
    permission="item:write",
    risk_tier="high",
    idempotency="dispatcher",
)
def post_cost(
    request: Request,
    body: CostCreate,
    principal: Principal = Depends(get_principal),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, object]:
    _require(principal, "item:write", permission_service)
    entity_id = uuid4()
    payload = body.model_dump(by_alias=True)
    with Session(request.app.state.database_engine) as session, session.begin():
        dispatcher = make_action_dispatcher(session, permission_service)
        result = dispatcher.dispatch(
            principal=principal,
            permission="item:write",
            risk_tier=RiskTier.HIGH,
            action="SkuCost.create",
            entity="SkuCost",
            entity_id=entity_id,
            payload=payload,
            expected_version=body.expected_version,
            idempotency_key=idempotency_key,
            business_action=lambda: create_cost(
                session,
                entity_id=entity_id,
                internal_sku=body.internal_sku,
                period=body.period,
                amount_minor=body.unit_cost.amount_minor,
                currency=body.unit_cost.currency,
                source=body.source,
                principal=principal,
                permission_service=permission_service,
            ),
        )
    return cast(dict[str, object], result)


__all__ = ["router"]
