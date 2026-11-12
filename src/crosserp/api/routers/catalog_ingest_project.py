"""导入批次投射与真人替代接口。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _write_guard
from crosserp.catalog.ingest_project import project_batch, supersede_batch
from crosserp.db.schema import ImportBatch
from crosserp.platform.approval import ApprovalGateway
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier

router = APIRouter()


def _dispatcher(request: Request, session: Session) -> ActionDispatcher:
    return ActionDispatcher(
        session=session,
        permission_service=request.app.state.permission_service,
        approval_gateway=_approval_gateway(session),
    )


def _approval_gateway(session: Session) -> ApprovalGateway:
    from crosserp.approval.gateway import ApprovalGatewayImpl

    return ApprovalGatewayImpl(session)


@router.post("/ingest/batches/{id}/project")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.project",
    permission="integration:import",
    risk_tier="medium",
)
def project(
    request: Request,
    id: UUID,
    payload: dict[str, Any] | None = Body(default=None),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        batch = session.get(ImportBatch, id)
        if batch is None:
            raise not_found(message="导入批次不存在")
        body = payload or {}
        expected = body.get("expectedVersion")
        if expected is not None and int(expected) != batch.version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "导入批次版本已变化",
                details={"expectedVersion": int(expected), "actualVersion": batch.version},
            )
        if batch.status == "projected":
            request.app.state.permission_service.require(principal, "integration:import")
            return project_batch(
                session,
                id,
                principal=principal,
                permission_service=request.app.state.permission_service,
                request_id=request.state.request_id,
                idempotency_key=idempotency_key,
                payload=body,
            )
        result = _dispatcher(request, session).dispatch(
            principal=principal,
            permission="integration:import",
            risk_tier=RiskTier.MEDIUM,
            action="IngestBatch.project",
            entity="IngestBatch",
            entity_id=id,
            payload=body,
            idempotency_key=idempotency_key,
            source_batch_id=id,
            source_file=batch.file_name,
            source_rule_version=batch.mapping_rule_version,
            request_id=request.state.request_id,
            business_action=lambda: project_batch(
                session,
                id,
                principal=principal,
                permission_service=request.app.state.permission_service,
                request_id=request.state.request_id,
                idempotency_key=idempotency_key,
                payload=body,
            ),
        )
        session.commit()
        result_dict = cast(dict[str, Any], result)
        result_dict["version"] = batch.version
        return result_dict
    finally:
        session.close()


@router.post("/ingest/batches/{id}/supersede")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.supersede",
    permission="integration:import",
    risk_tier="critical",
)
def supersede(
    request: Request,
    id: UUID,
    payload: dict[str, Any] | None = Body(default=None),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        old = session.get(ImportBatch, id)
        if old is None:
            raise not_found(message="导入批次不存在")
        body = payload or {}
        replacement = (
            body.get("newBatchId") or body.get("replacementBatchId") or body.get("batchId")
        )
        if replacement is None:
            raise APIError(ErrorCode.VALIDATION_ERROR, "缺少 newBatchId")
        new_id = UUID(str(replacement))
        expected = body.get("expectedVersion")
        if expected is not None and int(expected) != old.version:
            raise APIError(
                ErrorCode.CONFLICT_VERSION,
                "导入批次版本已变化",
                details={"expectedVersion": int(expected), "actualVersion": old.version},
            )
        result = _dispatcher(request, session).dispatch(
            principal=principal,
            permission="integration:import",
            risk_tier=RiskTier.CRITICAL,
            action="IngestBatch.supersede",
            entity="IngestBatch",
            entity_id=id,
            payload=body,
            idempotency_key=idempotency_key,
            source_batch_id=id,
            source_file=old.file_name,
            source_rule_version=old.mapping_rule_version,
            request_id=request.state.request_id,
            business_action=lambda: supersede_batch(
                session, id, new_batch_id=new_id, principal=principal
            ),
        )
        session.commit()
        result_dict = cast(dict[str, Any], result)
        result_dict["version"] = old.version
        return result_dict
    finally:
        session.close()


__all__ = ["router"]
