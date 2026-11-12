"""导入批次、原始记录、清洗问题和映射规则只读接口。"""

# ruff: noqa: B008

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _page, _principal_db, _require
from crosserp.api.schemas import PageParams
from crosserp.db.schema import CleansingIssue, ImportBatch, MappingRule, RawRow
from crosserp.platform.audit import DefaultAuditRecorder

router = APIRouter()

_SENSITIVE_TOKENS = ("password", "secret", "token", "api_key", "apikey", "phone", "email", "bank")


def _batch_payload(row: ImportBatch) -> dict[str, Any]:
    counts = {
        "landed": row.landed_count,
        "valid": row.valid_count,
        "duplicate": row.duplicate_count,
        "quarantined": row.quarantined_count,
        "projected": row.projected_count,
    }
    return {
        "id": str(row.id),
        "source": row.source,
        "kind": row.kind,
        "status": row.status,
        "fileSha256": row.file_sha256,
        "mappingRuleVersion": row.mapping_rule_version,
        "counts": counts,
        "supersedes": str(row.supersedes_id) if row.supersedes_id else None,
        "createdBy": str(row.created_by) if row.created_by else None,
        "onBehalfOf": str(row.on_behalf_of) if row.on_behalf_of else None,
        "createdAt": (row.received_at or row.imported_at).isoformat(),
        "version": row.version,
    }


def _contains_sensitive(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            any(token in str(key).casefold() for token in _SENSITIVE_TOKENS)
            or _contains_sensitive(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive(item) for item in value)
    return False


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***"
            if any(token in str(key).casefold() for token in _SENSITIVE_TOKENS)
            else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@contextmanager
def _ingest_session(request: Request) -> Iterator[tuple[Any, Session]]:
    principal, session = _principal_db(request)
    session.rollback()
    try:
        with session.begin():
            _require(request, principal, "integration:read", entity="IngestBatch")
            yield principal, session
    finally:
        session.close()


@router.get("/ingest/batches")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_batches(
    request: Request,
    params: PageParams = Depends(),
    q: str | None = Query(None),
    sort: str = Query("-createdAt"),
) -> dict[str, Any]:
    with _ingest_session(request) as (_principal, session):
        if sort not in {"createdAt", "-createdAt", "status", "-status"}:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 参数无效")
        rows = list(
            session.scalars(
                select(ImportBatch).order_by(ImportBatch.imported_at.desc(), ImportBatch.id.desc())
            )
        )
        if sort == "createdAt":
            rows.reverse()
        elif sort == "status":
            rows.sort(key=lambda row: (row.status, str(row.id)))
        elif sort == "-status":
            rows.sort(key=lambda row: (row.status, str(row.id)), reverse=True)
        if q:
            rows = [
                row
                for row in rows
                if q.casefold() in row.file_name.casefold()
                or q.casefold() in row.kind.casefold()
                or q.casefold() in row.status.casefold()
            ]
        start = (params.page - 1) * params.page_size
        return _page(
            params,
            [_batch_payload(row) for row in rows[start : start + params.page_size]],
            len(rows),
        )


@router.get("/ingest/batches/{id}")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.get",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def get_batch(request: Request, id: UUID) -> dict[str, Any]:
    with _ingest_session(request) as (_principal, session):
        batch = session.get(ImportBatch, id)
        if batch is None:
            raise not_found()
        return _batch_payload(batch)


@router.get("/ingest/batches/{id}/raw-records")
@api_endpoint(
    entity="RawRecord",
    action="RawRecord.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_raw_records(
    request: Request,
    id: UUID,
    params: PageParams = Depends(),
    q: str | None = Query(None),
    sort: str = Query("rowNo"),
) -> dict[str, Any]:
    with _ingest_session(request) as (principal, session):
        batch = session.get(ImportBatch, id)
        if batch is None:
            raise not_found()
        if sort not in {"rowNo", "-rowNo"}:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 参数无效")
        rows = list(
            session.scalars(
                select(RawRow).where(RawRow.batch_id == id).order_by(RawRow.row_no.asc())
            )
        )
        if sort == "-rowNo":
            rows.reverse()
        if q:
            rows = [row for row in rows if q.casefold() in str(row.payload_json).casefold()]
        items = []
        sensitive_read = False
        for row in rows:
            sensitive_read |= _contains_sensitive(row.payload_json)
            items.append(
                {
                    "id": row.id,
                    "batchId": str(row.batch_id),
                    "rowNo": row.row_no,
                    "payload": _redact(row.payload_json),
                    "sha256": row.sha256,
                    "receivedAt": (row.received_at or batch.imported_at).isoformat(),
                }
            )
        if sensitive_read:
            DefaultAuditRecorder(session).record(
                principal=principal,
                entity="RawRecord",
                action="RawRecord.list",
                diff={"batchId": str(id), "sensitive": True},
                request_id=request.state.request_id,
                reason="读取敏感原始字段",
            )
        start = (params.page - 1) * params.page_size
        return _page(params, items[start : start + params.page_size], len(items))


@router.get("/ingest/batches/{id}/issues")
@api_endpoint(
    entity="CleansingIssue",
    action="CleansingIssue.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_issues(
    request: Request,
    id: UUID,
    params: PageParams = Depends(),
    q: str | None = Query(None),
    sort: str = Query("rowNo"),
) -> dict[str, Any]:
    with _ingest_session(request) as (_principal, session):
        batch = session.get(ImportBatch, id)
        if batch is None:
            raise not_found()
        if sort not in {"rowNo", "-rowNo"}:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 参数无效")
        rows = list(
            session.scalars(
                select(CleansingIssue)
                .where(CleansingIssue.batch_id == id)
                .order_by(CleansingIssue.row_no.asc())
            )
        )
        if sort == "-rowNo":
            rows.reverse()
        if q:
            rows = [
                row
                for row in rows
                if q.casefold() in row.message.casefold() or q.casefold() in row.kind.casefold()
            ]
        items = [
            {
                "id": str(row.id),
                "batchId": str(row.batch_id),
                "rowNo": row.row_no,
                "kind": row.kind,
                "field": row.field,
                "message": row.message,
                "suggestion": row.suggestion_json,
                "status": row.status,
                "createdAt": row.created_at.isoformat(),
            }
            for row in rows
        ]
        start = (params.page - 1) * params.page_size
        return _page(params, items[start : start + params.page_size], len(items))


@router.get("/finance/fee-map")
@router.get("/finance/column-maps")
@router.get("/ingest/mapping-rules")
@api_endpoint(
    entity="MappingRule",
    action="MappingRule.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_mapping_rules(
    request: Request,
    params: PageParams = Depends(),
    q: str | None = Query(None),
    sort: str = Query("-createdAt"),
) -> dict[str, Any]:
    with _ingest_session(request) as (_principal, session):
        if sort not in {"createdAt", "-createdAt", "ruleVersion", "-ruleVersion"}:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 参数无效")
        rows = list(
            session.scalars(
                select(MappingRule).order_by(MappingRule.created_at.desc(), MappingRule.id.desc())
            )
        )
        if sort == "createdAt":
            rows.reverse()
        elif sort == "ruleVersion":
            rows.sort(key=lambda row: row.rule_version)
        elif sort == "-ruleVersion":
            rows.sort(key=lambda row: row.rule_version, reverse=True)
        if q:
            rows = [
                row
                for row in rows
                if q.casefold() in row.rule_key.casefold()
                or q.casefold() in row.rule_version.casefold()
                or q.casefold() in row.kind.casefold()
            ]
        items = [
            {
                "id": str(row.id),
                "ruleKey": row.rule_key,
                "kind": row.kind,
                "version": row.rule_version,
                "ruleVersion": row.rule_version,
                "body": row.body_json,
                "status": row.status,
                "verified": row.verified,
                "createdAt": row.created_at.isoformat(),
                "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
        start = (params.page - 1) * params.page_size
        return _page(params, items[start : start + params.page_size], len(items))


__all__ = ["router"]
