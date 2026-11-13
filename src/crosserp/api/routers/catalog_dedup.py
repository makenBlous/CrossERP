"""疑似重复实体 JSON API。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _require, _write_guard
from crosserp.api.schemas import CamelModel, PageParams
from crosserp.catalog.dedup import candidate_ids, candidate_visible, merge_candidate
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.db.schema import DedupCandidate
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["数据进入与溯源"])


class MergeRequest(CamelModel):
    expected_version: int = Field(alias="expectedVersion", ge=1)
    target_id: str = Field(alias="targetId")


_ENTITY_WRITE_PERMISSIONS = {
    "Sku": "sku:write",
    "Supplier": "supplier:write",
    "Customer": "customer:write",
}


def _candidate_payload(row: DedupCandidate) -> dict[str, Any]:
    return {
        "candidateId": str(row.id),
        "entityType": row.entity_type,
        "ids": row.ids,
        "reason": row.reason,
        "confidence": row.confidence,
        "status": row.status,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance,
        "mergedTargetId": row.merged_target_id,
    }


def _require_candidate_scope(
    session: Session,
    candidate: DedupCandidate,
    principal: Principal,
    permission_service: Any,
) -> None:
    if not candidate_visible(session, candidate, principal, permission_service):
        raise APIError(ErrorCode.DATA_SCOPE_DENIED, "数据不在当前范围内")


@router.get("/ingest/dedup-candidates")
@api_endpoint(
    entity="DedupCandidate",
    action="DedupCandidate.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_dedup_candidates(
    request: Request,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _require(request, principal, "integration:read", entity="DedupCandidate")
    sort_name = (sort or "-createdAt").lstrip("-")
    if sort_name not in {"createdAt", "updatedAt", "confidence", "status"}:
        raise APIError(ErrorCode.VALIDATION_FAILED, "sort 不受支持")
    with Session(request.app.state.database_engine, expire_on_commit=False) as session:
        rows = list(session.scalars(select(DedupCandidate)))
        for row in rows:
            candidate_ids(row.ids)
        rows = [
            row
            for row in rows
            if candidate_visible(session, row, principal, request.app.state.permission_service)
        ]
        if q:
            needle = q.casefold()
            rows = [
                row
                for row in rows
                if needle in row.entity_type.casefold()
                or needle in row.reason.casefold()
                or needle in row.status.casefold()
            ]
        key_map = {
            "createdAt": lambda row: row.created_at,
            "updatedAt": lambda row: row.updated_at,
            "confidence": lambda row: row.confidence,
            "status": lambda row: row.status,
        }
        rows.sort(key=key_map[sort_name], reverse=sort.startswith("-") if sort else True)
        total = len(rows)
        start = (params.page - 1) * params.page_size
        return {
            "items": [_candidate_payload(row) for row in rows[start : start + params.page_size]],
            "page": params.page,
            "pageSize": params.page_size,
            "total": total,
        }


@router.post("/ingest/dedup-candidates/{id}/merge")
@api_endpoint(
    entity="DedupCandidate",
    action="DedupCandidate.merge",
    permission="integration:write",
    risk_tier="medium",
    idempotency="dispatcher",
)
def merge_dedup_candidate(
    request: Request,
    id: str,
    payload: MergeRequest,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _write_guard(request, principal, csrf)
    if idempotency_key is not None and len(idempotency_key) > 255:
        raise APIError(ErrorCode.VALIDATION_FAILED, "Idempotency-Key 过长")
    _require(request, principal, "integration:write", entity="DedupCandidate")
    try:
        candidate_id = UUID(id)
    except ValueError as exc:
        raise not_found(message="疑似重复候选不存在") from exc
    with (
        Session(request.app.state.database_engine, expire_on_commit=False) as session,
        session.begin(),
    ):
        candidate = session.get(DedupCandidate, candidate_id)
        if candidate is None:
            raise not_found(message="疑似重复候选不存在")
        target_permission = _ENTITY_WRITE_PERMISSIONS.get(candidate.entity_type)
        if target_permission is None:
            raise not_found(message="该实体类型尚未注册合并处理器")
        _require(request, principal, target_permission, entity=candidate.entity_type)
        _require_candidate_scope(
            session, candidate, principal, request.app.state.permission_service
        )
        try:
            target = str(UUID(payload.target_id))
        except ValueError as exc:
            raise APIError(ErrorCode.VALIDATION_FAILED, "targetId 必须是 UUID") from exc
        result = make_action_dispatcher(
            session, request.app.state.permission_service, undo_restore=CATALOG_UNDO_RESTORE
        ).dispatch(
            principal=principal,
            permission="integration:write",
            risk_tier=RiskTier.MEDIUM,
            entity="DedupCandidate",
            entity_id=str(candidate.id),
            action="DedupCandidate.merge",
            idempotency_key=idempotency_key,
            payload=payload.model_dump(by_alias=True),
            request_id=request.state.request_id,
            business_action=lambda: merge_candidate(
                session,
                candidate,
                target_id=target,
                expected_version=payload.expected_version,
                principal=principal,
            ),
        )
        return cast(dict[str, Any], result)


__all__ = ["MergeRequest", "router"]
