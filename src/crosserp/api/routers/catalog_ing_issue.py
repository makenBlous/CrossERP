"""清洗问题动作 API。"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Request
from pydantic import Field
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _require, _write_guard
from crosserp.api.schemas import CamelModel
from crosserp.catalog.ing_issue import escalate as escalate_issue
from crosserp.catalog.ing_issue import get_issue
from crosserp.catalog.ing_issue import resolve as resolve_issue
from crosserp.db.schema import CleansingIssue, ImportBatch
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher

router = APIRouter()


class ResolveIssueRequest(CamelModel):
    decision: Literal["mapping", "duplicate", "ignore"]
    reason: str | None = None
    mapping: dict[str, Any] | None = None
    expected_version: int = Field(alias="expectedVersion", ge=1)


class EscalateIssueRequest(CamelModel):
    reason: str | None = None
    attempts: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
    suggestion: Any = None
    expected_version: int = Field(alias="expectedVersion", ge=1)


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
    raw_id, source_file = issue.raw_record_id, batch.file_name
    risk = RiskTier.HIGH if issue.money_impact else RiskTier.MEDIUM
    result = make_action_dispatcher(session, request.app.state.permission_service).dispatch(
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
    response = dict(result)
    response.setdefault("id", str(issue.id))
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
    payload: ResolveIssueRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        session.rollback()
        with session.begin():
            _write_guard(request, principal, csrf)
            _require(request, principal, "integration:import", entity="CleansingIssue")
            batch, issue = get_issue(session, id, issueId)
            values = payload.model_dump(by_alias=True)
            return _dispatch(
                request,
                session,
                principal,
                batch,
                issue,
                action="CleansingIssue.resolve",
                payload=values,
                expected_version=payload.expected_version,
                idempotency_key=idempotency_key,
                work=lambda: resolve_issue(
                    session,
                    issue,
                    decision=payload.decision,
                    reason=payload.reason,
                    mapping=payload.mapping,
                    handler="agent" if principal.is_agent else "admin",
                ),
            )
    finally:
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
    payload: EscalateIssueRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        session.rollback()
        with session.begin():
            _write_guard(request, principal, csrf)
            _require(request, principal, "integration:import", entity="CleansingIssue")
            batch, issue = get_issue(session, id, issueId)
            values = payload.model_dump(by_alias=True)
            return _dispatch(
                request,
                session,
                principal,
                batch,
                issue,
                action="CleansingIssue.escalate",
                payload=values,
                expected_version=payload.expected_version,
                idempotency_key=idempotency_key,
                work=lambda: escalate_issue(
                    session,
                    batch,
                    issue,
                    principal=principal,
                    reason=payload.reason,
                    attempts=payload.attempts,
                    evidence=payload.evidence,
                    suggestion=payload.suggestion,
                ),
            )
    finally:
        session.close()


__all__ = ["router"]
