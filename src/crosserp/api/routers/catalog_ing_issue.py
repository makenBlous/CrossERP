"""清洗问题动作 API。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _require, _write_guard
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.catalog.ing_issue import escalate as escalate_issue
from crosserp.catalog.ing_issue import get_issue
from crosserp.catalog.ing_issue import resolve as resolve_issue
from crosserp.db.schema import Approval, CleansingIssue, ImportBatch
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier

router = APIRouter()


def _expected_version(payload: dict[str, Any]) -> int:
    value = payload.get("expectedVersion")
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise APIError(ErrorCode.VALIDATION_ERROR, "expectedVersion 必须是正整数")
    return value


def _approval_payload(value: Approval, issue: CleansingIssue) -> dict[str, Any]:
    return {
        "id": str(issue.id),
        "status": value.state,
        "approvalId": str(value.id),
        "version": issue.version,
    }


def _dispatch(
    request: Request,
    session: Session,
    principal: Any,
    batch: ImportBatch,
    issue: CleansingIssue,
    *,
    action: str,
    payload: dict[str, Any],
    expected_version: int,
    idempotency_key: str | None,
    work: Any,
) -> dict[str, Any]:
    _require(request, principal, "integration:import", entity="CleansingIssue")
    if issue.version != expected_version:
        raise APIError(
            ErrorCode.CONFLICT_VERSION,
            "清洗问题版本已变化",
            details={"expectedVersion": expected_version, "version": issue.version},
        )
    raw_id, source_file = issue.raw_record_id, batch.file_name
    risk = RiskTier.HIGH if principal.is_agent and issue.money_impact else RiskTier.MEDIUM
    result = ActionDispatcher(
        session=session,
        permission_service=request.app.state.permission_service,
        audit_recorder=DefaultAuditRecorder(session),
        approval_gateway=ApprovalGatewayImpl(session),
    ).dispatch(
        principal=principal,
        permission="integration:import",
        risk_tier=risk,
        action=action,
        entity="CleansingIssue",
        entity_id=issue.id,
        payload=payload,
        expected_version=expected_version - 1,
        idempotency_key=idempotency_key,
        source_batch_id=issue.batch_id,
        source_raw_row_id=raw_id,
        source_file=source_file,
        request_id=request.state.request_id,
        business_action=work,
    )
    if isinstance(result, Approval):
        return _approval_payload(result, issue)
    response = dict(result)
    response["version"] = issue.version
    return response


@router.post("/ingest/batches/{id}/issues/{issueId}/resolve")
@api_endpoint(
    entity="CleansingIssue",
    action="CleansingIssue.resolve",
    permission="integration:import",
    risk_tier="medium",
)
def resolve(
    request: Request,
    id: UUID,
    issueId: UUID,
    payload: dict[str, Any] = Body(default={}),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:import", entity="CleansingIssue")
        batch, issue = get_issue(session, id, issueId)
        expected_version = _expected_version(payload)
        decision = payload.get("decision")
        if not isinstance(decision, str):
            raise APIError(ErrorCode.VALIDATION_ERROR, "decision 必填")
        mapping = payload.get("mapping")
        if mapping is not None and not isinstance(mapping, dict):
            raise APIError(ErrorCode.VALIDATION_ERROR, "mapping 必须是对象")

        return _dispatch(
            request,
            session,
            principal,
            batch,
            issue,
            action="CleansingIssue.resolve",
            payload=payload,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            work=lambda: resolve_issue(
                session,
                issue,
                decision=decision,
                reason=payload.get("reason"),
                mapping=mapping,
                handler="agent" if principal.is_agent else "admin",
            ),
        )
    finally:
        session.commit()
        session.close()


@router.post("/ingest/batches/{id}/issues/{issueId}/escalate")
@api_endpoint(
    entity="CleansingIssue",
    action="CleansingIssue.escalate",
    permission="integration:import",
    risk_tier="medium",
)
def escalate(
    request: Request,
    id: UUID,
    issueId: UUID,
    payload: dict[str, Any] = Body(default={}),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:import", entity="CleansingIssue")
        batch, issue = get_issue(session, id, issueId)
        expected_version = _expected_version(payload)
        attempts = payload.get("attempts", [])
        evidence = payload.get("evidence", [])
        if not isinstance(attempts, list) or not isinstance(evidence, list):
            raise APIError(ErrorCode.VALIDATION_ERROR, "attempts 和 evidence 必须是数组")
        return _dispatch(
            request,
            session,
            principal,
            batch,
            issue,
            action="CleansingIssue.escalate",
            payload=payload,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            work=lambda: escalate_issue(
                session,
                batch,
                issue,
                principal=principal,
                reason=payload.get("reason"),
                attempts=attempts,
                evidence=evidence,
                suggestion=payload.get("suggestion"),
            ),
        )
    finally:
        session.commit()
        session.close()


__all__ = ["router"]
