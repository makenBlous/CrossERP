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
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.catalog.ingest import MappingRuleBody
from crosserp.catalog.ingest_rules import save_mapping_rule_version
from crosserp.db.schema import MappingRule
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
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
)
def get_column_map(
    request: Request,
    id: UUID,
    principal_override: Principal = Depends(get_principal),
) -> dict[str, Any]:
    principal = principal_override
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
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }


@router.put("/finance/column-maps/{id}")
@router.put("/ingest/mapping-rules/{id}")
@api_endpoint(
    entity="MappingRule",
    action="MappingRule.update",
    permission="integration:write",
    risk_tier="high",
)
def update_mapping_rule(
    request: Request,
    id: UUID,
    body: MappingRuleUpdateBody,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal_override: Principal = Depends(get_principal),
) -> dict[str, Any]:
    principal = principal_override
    with Session(request.app.state.database_engine) as session, session.begin():
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:write", entity="MappingRule")
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
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=request.app.state.permission_service,
            approval_gateway=ApprovalGatewayImpl(session),
            audit_recorder=DefaultAuditRecorder(session),
        )
        payload = body.model_dump(by_alias=True)
        result = dispatcher.dispatch(
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
