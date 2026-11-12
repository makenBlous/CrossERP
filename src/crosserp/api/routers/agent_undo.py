"""智能体自动动作的每日摘要与撤销接口。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any, cast

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.metadata import api_endpoint
from crosserp.db.schema import EntityEvent
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal, get_principal

router = APIRouter(tags=["智能体中心"])


def _permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


@router.get("/agent/daily-summary")
@api_endpoint(
    entity="AgentSuggestion",
    action="AgentSuggestion.daily_summary",
    permission="agent_suggestion:read",
    risk_tier="none",
    idempotency="none",
)
def daily_summary(
    request: Request,
    day: date | None = Query(None),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    permission_service.require(principal, "agent_suggestion:read")
    selected_day = day or datetime.now(UTC).date()
    start = datetime.combine(selected_day, time.min, tzinfo=UTC)
    end = datetime.combine(selected_day, time.max, tzinfo=UTC)
    with Session(request.app.state.database_engine) as session:
        events = list(
            session.scalars(
                select(EntityEvent)
                .where(
                    EntityEvent.event_type == "notification.daily_summary",
                    EntityEvent.created_at >= start,
                    EntityEvent.created_at <= end,
                )
                .order_by(EntityEvent.created_at)
            )
        )
    effective_id = principal.effective_user_id
    items = [_summary_item(event) for event in events if _visible_to(event, effective_id)]
    return {
        "date": selected_day.isoformat(),
        "count": len(items),
        "message": f"AI 今天替你做了 {len(items)} 件事",
        "items": items,
    }


@router.post("/agent/suggestions/{id}/undo")
@api_endpoint(
    entity="AgentSuggestion",
    action="AgentSuggestion.undo",
    permission="agent_suggestion:create",
    risk_tier="critical",
    idempotency="dispatcher",
)
def undo_suggestion(
    id: str,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    permission_service: PermissionService = Depends(_permission_service),
) -> dict[str, Any]:
    permission_service.require(principal, "agent_suggestion:create")
    with Session(request.app.state.database_engine) as session, session.begin():
        dispatcher = make_action_dispatcher(session, permission_service)
        return dispatcher.undo(
            id,
            principal=principal,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )


def _visible_to(event: EntityEvent, effective_id: Any) -> bool:
    payload = dict(event.payload_json)
    return payload.get("onBehalfOf") == str(effective_id) or payload.get("actorUserId") == str(
        effective_id
    )


def _summary_item(event: EntityEvent) -> dict[str, Any]:
    payload = dict(event.payload_json)
    return {
        "id": str(event.id),
        "action": payload.get("action", event.action_id),
        "entityType": event.entity_type,
        "entityId": event.entity_id,
        "riskTier": payload.get("riskTier"),
        "at": event.created_at.isoformat(),
        "reversibleUntil": payload.get("reversibleUntil"),
        "undoId": payload.get("undoId"),
    }


__all__ = ["router"]
