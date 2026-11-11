"""本体目录、实体版本和溯源 JSON 接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.db.schema import EntityVersion
from crosserp.ontology.catalog import ActionTypeDef, EntityTypeDef, load_catalog
from crosserp.platform.dispatcher import AutonomyDecision, can_ai_execute
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["本体与实体目录"])
_CATALOG = load_catalog()


def _permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "pageSize": page_size, "total": total}


def _require(principal: Principal, permission: str, service: PermissionService) -> None:
    service.require(principal, permission)


def _entity_or_404(entity_type: str) -> EntityTypeDef:
    entity = _CATALOG.entity_by_id.get(entity_type)
    if entity is None:
        raise not_found(message="实体类型不存在")
    return entity


def _action_or_404(action_id: str) -> ActionTypeDef:
    action = _CATALOG.action_by_id.get(action_id)
    if action is None:
        raise not_found(message="实体动作不存在")
    return action


@router.get("/ontology/entity-types")
@api_endpoint(
    entity="EntityType", action="EntityType.list", permission="authenticated", risk_tier="none"
)
def list_entity_types(
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    values = list(_CATALOG.entity_types)
    if q:
        values = [x for x in values if q.casefold() in (x.id + x.name_zh).casefold()]
    if sort and sort.lstrip("-") == "id":
        values.sort(key=lambda x: x.id, reverse=sort.startswith("-"))
    total = len(values)
    start = (page - 1) * page_size
    return _page([x.as_dict() for x in values[start : start + page_size]], page, page_size, total)


@router.get("/ontology/entity-types/{type}")
@api_endpoint(
    entity="EntityType", action="EntityType.get", permission="authenticated", risk_tier="none"
)
def get_entity_type(
    type: str,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    return _entity_or_404(type).as_dict()


@router.get("/ontology/actions")
@api_endpoint(
    entity="ActionType", action="ActionType.list", permission="authenticated", risk_tier="none"
)
def list_actions(
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    values = list(_CATALOG.actions)
    if q:
        values = [x for x in values if q.casefold() in (x.id + x.summary).casefold()]
    if sort and sort.lstrip("-") == "id":
        values.sort(key=lambda x: x.id, reverse=sort.startswith("-"))
    total = len(values)
    start = (page - 1) * page_size
    return _page([x.as_dict() for x in values[start : start + page_size]], page, page_size, total)


@router.post("/ontology/actions/{actionId}/dry-run")
@api_endpoint(
    entity="ActionType", action="ActionType.dry_run", permission="authenticated", risk_tier="none"
)
def dry_run(
    actionId: str,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    action = _action_or_404(actionId)
    decision = can_ai_execute(action.risk_tier) if principal.is_agent else AutonomyDecision.EXECUTE
    if principal.is_agent and decision is AutonomyDecision.REJECT:
        return {
            "actionId": actionId,
            "wouldExecute": False,
            "decision": decision.value,
            "reason": "AI_AUTONOMY_CAPPED",
        }
    return {
        "actionId": actionId,
        "wouldExecute": decision is AutonomyDecision.EXECUTE,
        "decision": decision.value,
        "riskTier": action.risk_tier,
        "permission": action.permission,
        "approval": "required" if decision is AutonomyDecision.DRAFT_OR_APPROVAL else "none",
        "payload": {} if body is None else body,
    }


@router.get("/ontology/event-types")
@api_endpoint(
    entity="EventType", action="EventType.list", permission="system:read", risk_tier="none"
)
def list_event_types(
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    _require(principal, "system:read", permission_service)
    values = list(_CATALOG.events)
    if q:
        values = [x for x in values if q.casefold() in x.id.casefold()]
    total = len(values)
    start = (page - 1) * page_size
    return _page([x.as_dict() for x in values[start : start + page_size]], page, page_size, total)


@router.get("/entities/{type}/{id}/versions")
@api_endpoint(
    entity="EntityVersion",
    action="EntityVersion.list",
    permission="authenticated",
    risk_tier="none",
)
def list_versions(
    request: Request,
    type: str,
    id: str,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    _entity_or_404(type)
    with Session(request.app.state.database_engine) as session:
        statement = select(EntityVersion).where(
            EntityVersion.entity_type == type, EntityVersion.entity_id == id
        )
        if q:
            statement = statement.where(EntityVersion.action_id.contains(q))
        count = session.scalar(select(func.count()).select_from(statement.subquery()))
        total = 0 if count is None else int(count)
        if total == 0:
            raise not_found(message="实体不存在")
        rows = list(
            session.scalars(
                statement.order_by(EntityVersion.version.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
    if not rows:
        raise not_found(message="实体不存在")
    return _page([_version_dict(row) for row in rows], page, page_size, total)


@router.get("/entities/{type}/{id}/versions/{version}")
@api_endpoint(
    entity="EntityVersion", action="EntityVersion.get", permission="authenticated", risk_tier="none"
)
def get_version(
    request: Request,
    type: str,
    id: str,
    version: str,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    _entity_or_404(type)
    try:
        number = int(version)
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, "version 必须是整数") from exc
    with Session(request.app.state.database_engine) as session:
        row = session.scalar(
            select(EntityVersion).where(
                EntityVersion.entity_type == type,
                EntityVersion.entity_id == id,
                EntityVersion.version == number,
            )
        )
    if row is None:
        raise not_found(message="实体版本不存在")
    return _version_dict(row)


@router.get("/entities/{type}/{id}/lineage")
@api_endpoint(
    entity="EntityVersion",
    action="EntityVersion.read_lineage",
    permission="authenticated",
    risk_tier="none",
)
def lineage(
    request: Request,
    type: str,
    id: str,
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    _require(principal, "authenticated", permission_service)
    _entity_or_404(type)
    with Session(request.app.state.database_engine) as session:
        rows = list(
            session.scalars(
                select(EntityVersion)
                .where(EntityVersion.entity_type == type, EntityVersion.entity_id == id)
                .order_by(EntityVersion.version)
            )
        )
    if not rows:
        raise not_found(message="实体不存在")
    nodes: list[dict[str, Any]] = [
        {"id": f"{type}:{id}", "kind": "entity", "label": type, "visible": True}
    ]
    edges: list[dict[str, str]] = []
    for row in rows:
        node_id = f"version:{row.id}"
        nodes.append(
            {"id": node_id, "kind": "entity_version", "label": f"v{row.version}", "visible": True}
        )
        edges.append({"from": node_id, "to": f"{type}:{id}", "via": row.action_id or "version"})
        if row.source_batch_id:
            source_id = f"batch:{row.source_batch_id}"
            nodes.append(
                {"id": source_id, "kind": "raw_record", "label": "source batch", "visible": True}
            )
            edges.append({"from": source_id, "to": node_id, "via": "source_batch_id"})
    return {"entity": {"type": type, "id": id}, "nodes": nodes, "edges": edges}


def _version_dict(row: EntityVersion) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "entityType": row.entity_type,
        "entityId": row.entity_id,
        "version": row.version,
        "at": row.changed_at.isoformat(),
        "actorType": row.actor_type,
        "actorId": str(row.actor_id) if row.actor_id else None,
        "onBehalfOf": str(row.on_behalf_of) if row.on_behalf_of else None,
        "delegationId": row.delegation_id,
        "actionId": row.action_id,
        "batchId": str(row.source_batch_id) if row.source_batch_id else None,
        "diff": row.diff_json,
        "before": row.before_json,
        "after": row.after_json,
        "auditLogId": str(row.audit_log_id) if row.audit_log_id else None,
    }


__all__ = ["router"]
