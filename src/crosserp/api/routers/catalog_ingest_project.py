"""导入批次投射与真人替代接口。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request
from pydantic import Field

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _write_guard
from crosserp.api.schemas import CamelModel
from crosserp.catalog.ingest_project import project_batch, supersede_batch
from crosserp.db.schema import ImportBatch
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher

router = APIRouter()


class _ProjectRequest(CamelModel):
    expected_version: int | None = Field(default=None, ge=1)


class _SupersedeRequest(CamelModel):
    new_batch_id: UUID
    expected_version: int | None = Field(default=None, ge=1)


@router.post("/ingest/batches/{id}/project")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.project",
    permission="integration:import",
    risk_tier="medium",
    idempotency="dispatcher",
)
def project(
    request: Request,
    id: UUID,
    payload: _ProjectRequest | None = Body(default=None),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    with session:
        _write_guard(request, principal, csrf)
        session.rollback()
        with session.begin():
            batch = session.get(ImportBatch, id)
            if batch is None:
                raise not_found(message="导入批次不存在")
            body = {} if payload is None else payload.model_dump(by_alias=True, exclude_none=True)
            if (
                payload is not None
                and payload.expected_version is not None
                and payload.expected_version != batch.version
            ):
                raise APIError(
                    ErrorCode.CONFLICT_VERSION,
                    "导入批次版本已变化",
                    details={
                        "expectedVersion": payload.expected_version,
                        "actualVersion": batch.version,
                    },
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
            result = make_action_dispatcher(session, request.app.state.permission_service).dispatch(
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
            result_dict = cast(dict[str, Any], result)
            result_dict["version"] = batch.version
            return result_dict


@router.post("/ingest/batches/{id}/supersede")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.supersede",
    permission="integration:import",
    risk_tier="critical",
    idempotency="dispatcher",
)
def supersede(
    request: Request,
    id: UUID,
    payload: _SupersedeRequest = Body(...),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    with session:
        _write_guard(request, principal, csrf)
        session.rollback()
        with session.begin():
            old = session.get(ImportBatch, id)
            if old is None:
                raise not_found(message="导入批次不存在")
            body = payload.model_dump(by_alias=True, exclude_none=True)
            if payload.expected_version is not None and payload.expected_version != old.version:
                raise APIError(
                    ErrorCode.CONFLICT_VERSION,
                    "导入批次版本已变化",
                    details={
                        "expectedVersion": payload.expected_version,
                        "actualVersion": old.version,
                    },
                )
            result = make_action_dispatcher(session, request.app.state.permission_service).dispatch(
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
                    session, id, new_batch_id=payload.new_batch_id, principal=principal
                ),
            )
            result_dict = cast(dict[str, Any], result)
            result_dict["version"] = old.version
            return result_dict


__all__ = ["router"]
