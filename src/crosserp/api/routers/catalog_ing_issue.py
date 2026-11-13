"""清洗问题动作 API。"""

from __future__ import annotations

from typing import Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Header, Request
from pydantic import Field
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _principal_db, _require, _write_guard
from crosserp.api.schemas import CamelModel
from crosserp.catalog.ing_issue import escalate as escalate_issue
from crosserp.catalog.ing_issue import get_issue, require_issue_scope, resolve_command
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.db.schema import CleansingIssue, ImportBatch
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher

router = APIRouter()


class ResolveIssueRequest(CamelModel):
    decision: Literal["mapping", "duplicate", "ignore"]
    reason: str | None = None
    mapping: dict[str, Any] | None = None
    expected_version: int = Field(alias="expectedVersion", ge=0)


class EscalateIssueRequest(CamelModel):
    reason: str | None = None
    attempts: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
    suggestion: Any = None
    expected_version: int = Field(alias="expectedVersion", ge=0)


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
    dispatcher: Any,
) -> Any:
    risk = (
        RiskTier.HIGH
        if action == "CleansingIssue.resolve" and issue.money_impact
        else RiskTier.MEDIUM
    )
    return dispatcher.dispatch(
        principal=principal,
        permission="integration:import",
        risk_tier=risk,
        action=action,
        entity="CleansingIssue",
        entity_id=issue.id,
        payload=payload,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
        source_batch_id=issue.batch_id,
        source_raw_row_id=issue.raw_record_id,
        source_file=batch.file_name,
        request_id=request.state.request_id,
        business_action=work,
    )


def _agent_approval_response(issue: CleansingIssue, approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(issue.id),
        "status": approval["state"],
        "approvalId": approval["approvalId"],
        "version": issue.version,
    }


@router.post("/ingest/batches/{id}/issues/{issueId}/resolve")
@api_endpoint(
    entity="CleansingIssue",
    action="CleansingIssue.resolve",
    permission="integration:import",
    risk_tier="medium",
    idempotency="dispatcher",
)
def resolve(
    request: Request,
    id: UUID,
    issueId: UUID,
    payload: ResolveIssueRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, auth_session = _principal_db(request)
    auth_session.close()
    with Session(request.app.state.database_engine) as session, session.begin():
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:import", entity="CleansingIssue")
        batch, issue = get_issue(session, id, issueId)
        permission_service = request.app.state.permission_service
        require_issue_scope(session, principal, permission_service, issue, write=True)
        dispatcher = make_action_dispatcher(
            session, permission_service, undo_restore=CATALOG_UNDO_RESTORE
        )
        values = payload.model_dump(by_alias=True)
        result = _dispatch(
            request,
            session,
            principal,
            batch,
            issue,
            action="CleansingIssue.resolve",
            payload=values,
            expected_version=payload.expected_version,
            idempotency_key=idempotency_key,
            dispatcher=dispatcher,
            work=lambda: resolve_command(
                session,
                issue,
                principal=principal,
                decision=payload.decision,
                reason=payload.reason,
                mapping=payload.mapping,
                expected_version=payload.expected_version,
                request_id=request.state.request_id,
                payload=values,
                approval_gateway=dispatcher.approval_gateway,
            ),
        )
        if issue.money_impact and principal.is_agent:
            return _agent_approval_response(issue, result)
        return cast(dict[str, Any], result)


@router.post("/ingest/batches/{id}/issues/{issueId}/escalate")
@api_endpoint(
    entity="CleansingIssue",
    action="CleansingIssue.escalate",
    permission="integration:import",
    risk_tier="medium",
    idempotency="dispatcher",
)
def escalate(
    request: Request,
    id: UUID,
    issueId: UUID,
    payload: EscalateIssueRequest,
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, auth_session = _principal_db(request)
    auth_session.close()
    with Session(request.app.state.database_engine) as session, session.begin():
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:import", entity="CleansingIssue")
        batch, issue = get_issue(session, id, issueId)
        permission_service = request.app.state.permission_service
        require_issue_scope(session, principal, permission_service, issue, write=True)
        dispatcher = make_action_dispatcher(
            session, permission_service, undo_restore=CATALOG_UNDO_RESTORE
        )
        values = payload.model_dump(by_alias=True)
        return cast(
            dict[str, Any],
            _dispatch(
                request,
                session,
                principal,
                batch,
                issue,
                action="CleansingIssue.escalate",
                payload=values,
                expected_version=payload.expected_version,
                idempotency_key=idempotency_key,
                dispatcher=dispatcher,
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
            ),
        )


__all__ = ["router"]
