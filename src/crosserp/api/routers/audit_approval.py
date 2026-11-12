"""P0-03a 审计与审批中心 JSON API。"""
# ruff: noqa: B008

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import CamelModel
from crosserp.audit.log import verify_chain
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.db.schema import (
    Approval,
    ArchiveRun,
    AuditAlert,
    AuditExport,
    AuditLog,
    FileObject,
    RetentionPolicy,
    SecurityEvent,
)
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()


class AuditExportFilters(CamelModel):
    action: str | None = None
    actor_type: str | None = None
    target_type: str | None = None


class AuditExportBody(CamelModel):
    format: Literal["jsonl"] = "jsonl"
    from_ts: datetime | None = Field(default=None, alias="from")
    to_ts: datetime | None = Field(default=None, alias="to")
    filters: AuditExportFilters = Field(default_factory=AuditExportFilters)


class RetentionUpdateBody(CamelModel):
    chain: str = "audit_log"
    retain_days: int = Field(default=3650, alias="retainDays", gt=0)


def _session(request: Request) -> Session:
    return Session(request.app.state.database_engine)


def _auth(request: Request, principal: Principal, permission: str) -> None:
    request.app.state.permission_service.require(principal, permission)


def _log(row: AuditLog) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "seq": row.seq,
        "at": row.ts.isoformat(),
        "actorType": row.actor_type,
        "actorId": str(row.actor_user_id) if row.actor_user_id else None,
        "agentId": row.agent_id,
        "onBehalfOf": str(row.on_behalf_of) if row.on_behalf_of else None,
        "action": row.action,
        "refType": row.entity_type,
        "refId": row.entity_id,
        "diff": row.diff_json,
        "reason": row.reason,
        "evidence": row.evidence_json,
        "approvalId": str(row.approval_id) if row.approval_id else None,
        "channel": row.channel,
        "requestId": row.request_id,
        "ai": {
            "model": row.model,
            "promptVersion": row.prompt_version,
            "agentRunId": row.run_id,
            "llmCallId": row.llm_call,
            "confidence": row.confidence,
            "autonomyLevel": row.autonomy_level,
        },
        "prevHash": row.prev_hash,
        "hash": row.hash,
    }


def _approval(row: Approval) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "type": row.approval_type,
        "targetType": row.target_type,
        "targetId": row.target_id,
        "title": row.target_type,
        "status": row.state,
        "submitter": row.requested_by,
        "onBehalfOf": str(row.on_behalf_of) if row.on_behalf_of else None,
        "origin": row.actor_type,
        "payloadHash": row.payload_hash,
        "step": row.current_step,
        "resolution": row.resolution,
        "initiatorConfirmedBy": (
            str(row.initiator_confirmed_by) if row.initiator_confirmed_by else None
        ),
        "initiatorConfirmedAt": (
            row.initiator_confirmed_at.isoformat() if row.initiator_confirmed_at else None
        ),
        "initiatorConfirmationHash": row.initiator_confirmation_hash,
    }


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.get("/audit/logs")
@api_endpoint(
    entity="AuditLog",
    action="AuditLog.list",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def list_audit_logs(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session, session.begin():
        stmt = select(AuditLog).order_by(AuditLog.seq.desc())
        if q:
            stmt = stmt.where(
                AuditLog.action.contains(q)
                | AuditLog.target_type.contains(q)
                | AuditLog.target_id.contains(q)
            )
        rows = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
        total = session.scalar(select(func.count()).select_from(AuditLog))
        assert total is not None
        return _page([_log(row) for row in rows], page, page_size, total)


@router.get("/audit/logs/{id}")
@api_endpoint(
    entity="AuditLog",
    action="AuditLog.get",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def get_audit_log(
    id: str, request: Request, principal: Principal = Depends(get_principal)
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        try:
            row = session.get(AuditLog, UUID(id))
        except ValueError:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        return _log(row)


@router.get("/audit/chain")
@api_endpoint(
    entity="AuditLog",
    action="AuditLog.list",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def audit_chain(request: Request, principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        result = verify_chain(session)
        head = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()))
        return {
            "ok": result.ok,
            "checked": result.checked,
            "firstBadId": result.first_bad_id,
            "reason": result.reason,
            "head": _log(head) if head else None,
        }


@router.post("/audit/verify")
@api_endpoint(
    entity="AuditLog",
    action="AuditLog.create",
    permission="audit_log:read",
    risk_tier="low",
    idempotency="dispatcher",
)
def verify_audit(request: Request, principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session, session.begin():
        result: Any = make_action_dispatcher(
            session, request.app.state.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(
            principal=principal,
            permission="audit_log:read",
            risk_tier=RiskTier.LOW,
            action="AuditLog.create",
            business_action=lambda: verify_chain(session),
            request_id=request.state.request_id,
        )
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="AuditLog",
            action="AuditLog.create",
            diff={"ok": result.ok, "checked": result.checked},
            request_id=request.state.request_id,
        )
        return {
            "ok": result.ok,
            "checked": result.checked,
            "firstBadId": result.first_bad_id,
            "reason": result.reason,
        }


@router.post("/audit/exports")
@api_endpoint(
    entity="AuditExport",
    action="AuditExport.create",
    permission="audit_log:export",
    risk_tier="low",
    idempotency="http",
)
def create_audit_export(
    request: Request,
    body: AuditExportBody = Body(default_factory=AuditExportBody),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:export")

    with _session(request) as session, session.begin():
        statement = select(AuditLog).order_by(AuditLog.seq)
        if body.from_ts is not None:
            statement = statement.where(AuditLog.ts >= body.from_ts)
        if body.to_ts is not None:
            statement = statement.where(AuditLog.ts <= body.to_ts)
        if body.filters.action:
            statement = statement.where(AuditLog.action == body.filters.action)
        if body.filters.actor_type:
            statement = statement.where(AuditLog.actor_type == body.filters.actor_type)
        if body.filters.target_type:
            statement = statement.where(AuditLog.target_type == body.filters.target_type)
        rows = list(session.scalars(statement))
        content = (
            "\n".join(json.dumps(_log(row), ensure_ascii=False, sort_keys=True) for row in rows)
            + "\n"
        ).encode()
        now = datetime.now(UTC)
        from_ts = body.from_ts or (rows[0].ts if rows else now)
        to_ts = body.to_ts or (rows[-1].ts if rows else now)
        digest = hashlib.sha256(content).hexdigest()
        storage = request.app.state.file_storage
        storage_path = storage.write(digest, content)
        file_object = session.scalar(select(FileObject).where(FileObject.sha256 == digest))
        if file_object is None:
            file_object = FileObject(
                id=uuid4(),
                sha256=digest,
                filename="audit-export.jsonl",
                content_type="application/jsonl",
                size=len(content),
                storage_path=str(storage_path),
                uploaded_by=principal.effective_user_id or principal.user_id,
                created_at=now,
            )
            session.add(file_object)
            session.flush()
        else:
            storage_path = Path(file_object.storage_path)
        export_id = uuid4()
        export = AuditExport(
            id=export_id,
            requested_by=str(principal.user_id),
            actor_type=principal.actor_type.value,
            on_behalf_of=principal.on_behalf_of,
            from_ts=from_ts,
            to_ts=to_ts,
            format=body.format,
            chain="audit_log",
            filter_json=body.model_dump(mode="json", by_alias=True, exclude_none=True),
            row_count=len(rows),
            first_hash=rows[0].hash if rows else None,
            last_hash=rows[-1].hash if rows else None,
            file_sha256=digest,
            file_id=file_object.id,
            status="ready",
            created_at=now,
        )
        session.add(export)
        session.flush()
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="AuditExport",
            action="AuditExport.create",
            diff={
                "id": str(export.id),
                "rowCount": export.row_count,
                "fileId": str(file_object.id),
                "fileSha256": digest,
                "filters": export.filter_json,
            },
            request_id=request.state.request_id,
        )
        return {
            "id": str(export.id),
            "rowCount": export.row_count,
            "fileSha256": export.file_sha256,
            "status": "ready",
            "fileId": str(file_object.id),
        }


@router.get("/audit/exports/{id}/download")
@api_endpoint(
    entity="AuditExport",
    action="AuditExport.read_download",
    permission="audit_log:export",
    risk_tier="none",
    idempotency="none",
)
def download_audit_export(
    id: str, request: Request, principal: Principal = Depends(get_principal)
) -> Response:
    _auth(request, principal, "audit_log:export")
    with _session(request) as session:
        try:
            export = session.get(AuditExport, UUID(id))
        except ValueError:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
        if export is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        file_object = session.get(FileObject, export.file_id)
        if file_object is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        path = Path(file_object.storage_path)
        if not path.is_file():
            record_security(
                session,
                SecurityEventName.AUDIT_EXPORT_TAMPERED,
                user_id=principal.user_id,
                target_user_id=principal.effective_user_id,
                request_id=request.state.request_id,
                detail={
                    "exportId": str(export.id),
                    "fileId": str(file_object.id),
                    "reason": "missing",
                    "expectedSha256": export.file_sha256,
                },
            )
            DefaultAuditRecorder(session).record(
                principal=principal,
                entity="AuditExport",
                action="AuditExport.read_download",
                diff={"id": str(export.id), "status": "integrity_failed", "reason": "missing"},
                request_id=request.state.request_id,
            )
            session.commit()
            raise APIError(
                ErrorCode.AUDIT_EXPORT_INTEGRITY_ERROR,
                "审计导出文件完整性校验失败",
                details={"exportId": str(export.id), "reason": "missing"},
            )
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != export.file_sha256 or digest != file_object.sha256:
            record_security(
                session,
                SecurityEventName.AUDIT_EXPORT_TAMPERED,
                user_id=principal.user_id,
                target_user_id=principal.effective_user_id,
                request_id=request.state.request_id,
                detail={
                    "exportId": str(export.id),
                    "fileId": str(file_object.id),
                    "expectedSha256": export.file_sha256,
                    "actualSha256": digest,
                    "reason": "hash_mismatch",
                },
            )
            DefaultAuditRecorder(session).record(
                principal=principal,
                entity="AuditExport",
                action="AuditExport.read_download",
                diff={
                    "id": str(export.id),
                    "status": "integrity_failed",
                    "reason": "hash_mismatch",
                },
                request_id=request.state.request_id,
            )
            session.commit()
            raise APIError(
                ErrorCode.AUDIT_EXPORT_INTEGRITY_ERROR,
                "审计导出文件完整性校验失败",
                details={"exportId": str(export.id), "reason": "hash_mismatch"},
            )
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="AuditExport",
            action="AuditExport.read_download",
            diff={"id": str(export.id), "status": "downloaded"},
            request_id=request.state.request_id,
        )
        session.commit()
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="audit-{id}.jsonl"'},
        )


@router.get("/audit/security-events")
@api_endpoint(
    entity="SecurityEvent",
    action="SecurityEvent.list",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def security_events(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        rows = list(
            session.scalars(
                select(SecurityEvent)
                .order_by(SecurityEvent.seq.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        total = session.scalar(select(func.count()).select_from(SecurityEvent))
        assert total is not None
        return _page(
            [
                {
                    "id": str(r.id),
                    "seq": r.seq,
                    "event": r.event,
                    "at": r.ts.isoformat(),
                    "userId": str(r.user_id) if r.user_id else None,
                    "detail": r.detail_json,
                }
                for r in rows
            ],
            page,
            page_size,
            total,
        )


@router.get("/audit/agent-trace/{suggestionId}")
@api_endpoint(
    entity="AuditLog",
    action="AuditLog.get",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def agent_trace(
    suggestionId: str, request: Request, principal: Principal = Depends(get_principal)
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        rows = list(
            session.scalars(
                select(AuditLog)
                .where((AuditLog.entity_id == suggestionId) | (AuditLog.target_id == suggestionId))
                .order_by(AuditLog.seq)
            )
        )
        if not rows:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        return {"suggestionId": suggestionId, "items": [_log(row) for row in rows]}


@router.get("/audit/alerts")
@api_endpoint(
    entity="AuditAlert",
    action="AuditAlert.list",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def alerts(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        rows = list(
            session.scalars(
                select(AuditAlert)
                .order_by(AuditAlert.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        total = session.scalar(select(func.count()).select_from(AuditAlert))
        assert total is not None
        return _page(
            [
                {
                    "id": str(r.id),
                    "kind": r.kind,
                    "status": r.status,
                    "detail": r.detail_json,
                    "createdAt": r.created_at.isoformat(),
                }
                for r in rows
            ],
            page,
            page_size,
            total,
        )


@router.post("/audit/alerts/{id}/resolve")
@api_endpoint(
    entity="AuditAlert",
    action="AuditAlert.resolve",
    permission="audit_log:write",
    risk_tier="critical",
    idempotency="dispatcher",
)
def resolve_alert(
    id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:write")
    with _session(request) as session, session.begin():
        try:
            row = session.get(AuditAlert, UUID(id))
        except ValueError:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        make_action_dispatcher(
            session, request.app.state.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(
            principal=principal,
            permission="audit_log:write",
            risk_tier=RiskTier.CRITICAL,
            action="AuditAlert.resolve",
            business_action=lambda: setattr(row, "status", "resolved"),
            request_id=request.state.request_id,
        )
        row.resolved_at = datetime.now(UTC)
        row.resolved_by = principal.user_id
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="AuditAlert",
            action="AuditAlert.resolve",
            diff={"id": id, "status": row.status},
            request_id=request.state.request_id,
        )
        return {"id": id, "status": row.status}


@router.get("/audit/retention")
@api_endpoint(
    entity="RetentionPolicy",
    action="RetentionPolicy.list",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def retention(request: Request, principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        rows = list(session.scalars(select(RetentionPolicy).order_by(RetentionPolicy.chain)))
        return {
            "items": [
                {
                    "id": str(r.id),
                    "chain": r.chain,
                    "retainDays": r.retain_days,
                    "archiveBefore": r.archive_before.isoformat() if r.archive_before else None,
                }
                for r in rows
            ]
        }


@router.put("/audit/retention")
@api_endpoint(
    entity="RetentionPolicy",
    action="RetentionPolicy.update",
    permission="audit_log:write",
    risk_tier="critical",
    idempotency="dispatcher",
)
def update_retention(
    request: Request,
    body: RetentionUpdateBody,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:write")

    chain = body.chain
    with _session(request) as session, session.begin():
        row = session.scalar(select(RetentionPolicy).where(RetentionPolicy.chain == chain))
        if row is None:
            row = RetentionPolicy(
                id=uuid4(),
                chain=chain,
                retain_days=body.retain_days,
                updated_at=datetime.now(UTC),
            )
            session.add(row)
        else:
            row.retain_days = body.retain_days
            row.updated_at = datetime.now(UTC)
        row.updated_by = principal.user_id
        make_action_dispatcher(
            session, request.app.state.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(
            principal=principal,
            permission="audit_log:write",
            risk_tier=RiskTier.CRITICAL,
            action="RetentionPolicy.update",
            business_action=lambda: row,
            request_id=request.state.request_id,
        )
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="RetentionPolicy",
            action="RetentionPolicy.update",
            diff={"id": str(row.id), "chain": row.chain, "retainDays": row.retain_days},
            request_id=request.state.request_id,
        )
        return {"id": str(row.id), "chain": row.chain, "retainDays": row.retain_days}


@router.post("/audit/retention/archive")
@api_endpoint(
    entity="RetentionPolicy",
    action="RetentionPolicy.archive",
    permission="audit_log:write",
    risk_tier="critical",
    idempotency="dispatcher",
)
def archive_retention(
    request: Request,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(request, principal, "audit_log:write")
    with _session(request) as session, session.begin():
        rows = list(session.scalars(select(AuditLog).order_by(AuditLog.seq)))
        last = rows[-1] if rows else None
        run = ArchiveRun(
            id=uuid4(),
            chain="audit_log",
            upto_id=last.id if last else None,
            upto_hash=last.hash if last else "0" * 64,
            row_count=len(rows),
            created_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()
        make_action_dispatcher(
            session, request.app.state.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(
            principal=principal,
            permission="audit_log:write",
            risk_tier=RiskTier.CRITICAL,
            action="RetentionPolicy.archive",
            business_action=lambda: run,
            request_id=request.state.request_id,
        )
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="RetentionPolicy",
            action="RetentionPolicy.archive",
            diff={"id": str(run.id), "rowCount": run.row_count},
            request_id=request.state.request_id,
        )
        return {"id": str(run.id), "rowCount": run.row_count, "uptoHash": run.upto_hash}


@router.get("/audit/retention/archive-runs")
@api_endpoint(
    entity="RetentionPolicy",
    action="RetentionPolicy.read_archive_runs",
    permission="audit_log:read",
    risk_tier="none",
    idempotency="none",
)
def archive_runs(request: Request, principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    _auth(request, principal, "audit_log:read")
    with _session(request) as session:
        rows = list(session.scalars(select(ArchiveRun).order_by(ArchiveRun.created_at.desc())))
        return {
            "items": [
                {
                    "id": str(r.id),
                    "chain": r.chain,
                    "rowCount": r.row_count,
                    "uptoHash": r.upto_hash,
                    "createdAt": r.created_at.isoformat(),
                }
                for r in rows
            ]
        }
