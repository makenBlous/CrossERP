"""映射规则版本写入 API。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import Field, StrictInt
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _require, _write_guard
from crosserp.api.schemas import CamelModel
from crosserp.catalog.ingest import MappingRuleBody
from crosserp.catalog.ingest_rules import save_mapping_rule_version
from crosserp.db.schema import MappingRule
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()


class MappingRuleUpdateBody(CamelModel):
    expected_version: StrictInt = Field(alias="expectedVersion", ge=1)
    body: MappingRuleBody


@router.get("/finance/column-maps/{id}")
@api_endpoint(
    entity="MappingRule",
    action="MappingRule.get",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def get_column_map(
    request: Request,
    id: UUID,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    with Session(request.app.state.database_engine) as session:
        _require(request, principal, "integration:read", entity="MappingRule")
        row = session.get(MappingRule, id)
        if row is None:
            raise not_found()
        return {
            "id": str(row.id),
            "ruleKey": row.rule_key,
            "kind": row.kind,
            "ruleVersion": row.rule_version,
            "version": row.version,
            "body": row.body_json,
            "status": row.status,
            "verified": row.verified,
            "createdAt": row.created_at.isoformat(),
            "updatedAt": None if row.updated_at is None else row.updated_at.isoformat(),
        }


@router.put("/finance/column-maps/{id}")
@router.put("/ingest/mapping-rules/{id}")
@api_endpoint(
    entity="MappingRule",
    action="MappingRule.update",
    permission="integration:write",
    risk_tier="high",
    idempotency="dispatcher",
)
def update_mapping_rule(
    request: Request,
    id: UUID,
    body: MappingRuleUpdateBody,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    _require(request, principal, "integration:write", entity="MappingRule")
    payload = body.model_dump(by_alias=True)
    with Session(request.app.state.database_engine) as session, session.begin():
        current = session.get(MappingRule, id)
        if current is None:
            raise not_found()
        if body.expected_version != current.version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "实体版本已变化",
                details={
                    "expectedVersion": body.expected_version,
                    "actualVersion": current.version,
                },
            )
        result = make_action_dispatcher(session, permission_service).dispatch(
            principal=principal,
            permission="integration:write",
            risk_tier=RiskTier.HIGH,
            action="MappingRule.update",
            entity="MappingRule",
            entity_id=id,
            payload=payload,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
            business_action=lambda: save_mapping_rule_version(
                session, id, body=body.body, principal=principal
            ),
        )
    return cast(dict[str, Any], result)


__all__ = ["router"]
