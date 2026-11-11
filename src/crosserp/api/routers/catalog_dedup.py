"""疑似重复实体 JSON API。"""

# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _require, _write_guard
from crosserp.api.schemas import CamelModel, PageParams
from crosserp.catalog.dedup import merge_candidate
from crosserp.db.schema import AppUser, DedupCandidate, EntityVersion, UserRole
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["数据进入与溯源"])


class MergeRequest(CamelModel):
    expected_version: int | None = Field(default=None, alias="expectedVersion", ge=1)
    target_id: str | None = Field(default=None, alias="targetId")
    canonical_id: str | None = Field(default=None, alias="canonicalId")


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


def _principal_session(request: Request, principal: Principal) -> tuple[Principal, Session]:
    session = Session(request.app.state.database_engine, expire_on_commit=False)
    user = session.get(AppUser, principal.effective_user_id)
    if user is None or not user.is_active:
        session.close()
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    roles = frozenset(
        role for role in session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))
    )
    resolved = Principal(
        user_id=user.id,
        roles=roles,
        session_id=principal.session_id,
        actor_type=principal.actor_type,
        agent_id=principal.agent_id,
        on_behalf_of=principal.on_behalf_of,
        delegation_id=principal.delegation_id,
        run_id=principal.run_id,
        is_subagent=principal.is_subagent,
        channel=principal.channel,
        permissions=request.app.state.permission_service.current_permissions(principal),
        represented_permissions=principal.represented_permissions,
        data_scope=request.app.state.permission_service.data_scope_filter(principal, "UserAccount"),
    )
    return resolved, session


@router.get("/ingest/dedup-candidates")
@api_endpoint(
    entity="DedupCandidate",
    action="DedupCandidate.list",
    permission="integration:read",
    risk_tier="none",
)
def list_dedup_candidates(
    request: Request,
    params: Annotated[PageParams, Depends()],
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    principal, session = _principal_session(request, principal)
    try:
        _require(request, principal, "integration:read", entity="DedupCandidate")
        sort_name = (sort or "-createdAt").lstrip("-")
        if sort_name not in {"createdAt", "updatedAt", "confidence", "status"}:
            raise APIError(ErrorCode.VALIDATION_FAILED, "sort 不受支持")
        rows = list(session.scalars(select(DedupCandidate)))
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
    finally:
        session.close()


@router.post("/ingest/dedup-candidates/{id}/merge")
@api_endpoint(
    entity="DedupCandidate",
    action="DedupCandidate.merge",
    permission="integration:write",
    risk_tier="medium",
)
def merge_dedup_candidate(
    request: Request,
    id: str,
    payload: MergeRequest | None = None,
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    principal, session = _principal_session(request, principal)
    try:
        _write_guard(request, principal, csrf)
        _require(request, principal, "integration:write", entity="DedupCandidate")
        try:
            candidate_id = UUID(id)
        except ValueError as exc:
            raise not_found(message="疑似重复候选不存在") from exc
        candidate = session.get(DedupCandidate, candidate_id)
        if candidate is None:
            raise not_found(message="疑似重复候选不存在")
        body = MergeRequest() if payload is None else payload
        target = body.target_id or body.canonical_id
        if target is not None:
            try:
                target = str(UUID(target))
            except ValueError as exc:
                raise APIError(ErrorCode.VALIDATION_FAILED, "targetId 必须是 UUID") from exc
        current_entity_version = session.scalar(
            select(func.max(EntityVersion.version)).where(
                EntityVersion.entity_type == "DedupCandidate",
                EntityVersion.entity_id == str(candidate.id),
            )
        )
        result = ActionDispatcher(
            session=session,
            permission_service=request.app.state.permission_service,
        ).dispatch(
            principal=principal,
            permission="integration:write",
            risk_tier=RiskTier.MEDIUM,
            entity="DedupCandidate",
            entity_id=str(candidate.id),
            action="DedupCandidate.merge",
            expected_version=0 if current_entity_version is None else int(current_entity_version),
            idempotency_key=idempotency_key,
            payload=body.model_dump(by_alias=True),
            request_id=request.state.request_id,
            business_action=lambda: merge_candidate(
                session,
                candidate,
                target_id=target,
                expected_version=body.expected_version,
                principal=principal,
            ),
        )
        session.commit()
        return cast(dict[str, Any], result)
    finally:
        session.close()


__all__ = ["MergeRequest", "router"]
