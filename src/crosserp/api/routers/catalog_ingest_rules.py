"""映射规则版本写入 API。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _require, _write_guard
from crosserp.catalog.ingest_rules import save_mapping_rule_version
from crosserp.db.schema import MappingRule
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()


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
    principal, session = _principal_db(request, principal_override)
    try:
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
    finally:
        session.close()


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
    body: dict[str, Any] = Body(default_factory=dict),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal_override: Principal = Depends(get_principal),
) -> dict[str, Any]:
    principal, session = _principal_db(request, principal_override)
    try:
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:write", entity="MappingRule")
        current = session.get(MappingRule, id)
        if current is None:
            raise not_found()
        expected = body.get("expectedVersion")
        if expected is not None and int(expected) != current.version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "实体版本已变化",
                details={"expectedVersion": expected, "actualVersion": current.version},
            )
        from crosserp.approval.gateway import ApprovalGatewayImpl

        gateway: ApprovalGateway = ApprovalGatewayImpl(session)
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=request.app.state.permission_service,
            approval_gateway=gateway,
        )
        payload = dict(body)
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
                session, id, body=payload, principal=principal
            ),
        )
        return cast(dict[str, Any], result)
    finally:
        session.close()


__all__ = ["router"]
