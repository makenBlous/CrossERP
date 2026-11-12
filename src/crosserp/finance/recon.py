"""对账运行的查询与触发。计算复用 recon.engine。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import CamelModel
from crosserp.core.money import to_amount_minor
from crosserp.db.schema import EntityVersion, Issue, Match, ReconRun, Store
from crosserp.iam.scope import (
    apply_period_scope,
    apply_store_scope,
    period_contains,
    store_contains,
)
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal
from crosserp.recon.engine import reconcile

_SORTS = {
    "createdAt": ReconRun.started_at,
    "period": ReconRun.period,
    "matched": ReconRun.groups_matched,
    "status": ReconRun.status,
    "finishedAt": ReconRun.finished_at,
}


class ReconRunCreatePayload(CamelModel):
    store_id: UUID
    period: str = Field(min_length=7, max_length=7)
    as_of: date | None = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        year_text, separator, month_text = value.partition("-")
        if separator != "-" or len(year_text) != 4 or len(month_text) != 2:
            raise ValueError("period 必须是 YYYY-MM")
        if not year_text.isdigit() or not month_text.isdigit():
            raise ValueError("period 必须是 YYYY-MM")
        month = int(month_text)
        if not 1 <= month <= 12:
            raise ValueError("period 必须是 YYYY-MM")
        return value


def scope_denied(
    permission_service: PermissionService,
    principal: Principal,
    store_id: UUID,
    period: str,
) -> bool:
    stores = permission_service.store_scope(principal, "ReconRun")
    periods = permission_service.period_scope(principal, "ReconRun")
    return not store_contains(stores, store_id) or not period_contains(periods, period)


def list_recon_runs(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
) -> dict[str, Any]:
    permission_service.require(principal, "report:read")
    statement = _apply_scope(
        cast(Select[Any], select(ReconRun).join(Store, Store.id == ReconRun.store_id)),
        permission_service,
        principal,
    )
    if q:
        statement = statement.where(
            or_(ReconRun.period.ilike(f"%{q}%"), Store.name.ilike(f"%{q}%"))
        )
    total = cast(int, session.scalar(select(func.count()).select_from(statement.subquery())))
    ordering = _ordering(sort)
    runs = cast(
        list[ReconRun],
        list(
            session.scalars(
                statement.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
            )
        ),
    )
    stores = {
        row.id: row
        for row in session.scalars(
            select(Store).where(Store.id.in_([run.store_id for run in runs]))
        )
    }
    versions = _versions(session, [run.id for run in runs])
    issue_counts = _issue_counts(session, [run.id for run in runs])
    return {
        "items": [
            _run_dict(
                run,
                stores[run.store_id],
                version=versions.get(str(run.id)),
                issue_count=issue_counts.get(run.id, 0),
                detail=False,
                session=session,
                permission_service=permission_service,
                principal=principal,
            )
            for run in runs
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def get_recon_run(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    run_id: UUID,
) -> dict[str, Any]:
    permission_service.require(principal, "report:read")
    run = session.get(ReconRun, run_id)
    if run is None or scope_denied(permission_service, principal, run.store_id, run.period):
        raise not_found(message="对账运行不存在")
    store = session.get(Store, run.store_id)
    if store is None:
        raise not_found(message="对账运行不存在")
    versions = _versions(session, [run.id])
    counts = _issue_counts(session, [run.id])
    return _run_dict(
        run,
        store,
        version=versions.get(str(run.id)),
        issue_count=counts.get(run.id, 0),
        detail=True,
        session=session,
        permission_service=permission_service,
        principal=principal,
    )


def create_recon_run(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    payload: ReconRunCreatePayload,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    payload_data = payload.model_dump(by_alias=True, mode="json")
    run_id = uuid4()

    def before_replay(**_context: Any) -> None:
        if not idempotency_key:
            raise APIError(ErrorCode.VALIDATION_FAILED, "Idempotency-Key 必填", status_code=422)
        store = session.get(Store, payload.store_id)
        if store is None:
            raise not_found(message="店铺不存在")
        if scope_denied(permission_service, principal, payload.store_id, payload.period):
            raise APIError(ErrorCode.DATA_SCOPE_DENIED, "对账范围超出数据范围")

    def business_action() -> dict[str, Any]:
        reconcile(
            session,
            payload.store_id,
            payload.period,
            run_id=run_id,
            as_of=payload.as_of,
        )
        run = session.get(ReconRun, run_id)
        if run is None:
            raise APIError(ErrorCode.INTERNAL_ERROR, "对账运行未写入")
        run.created_by = str(principal.user_id)
        session.flush()
        store = session.get(Store, run.store_id)
        if store is None:
            raise APIError(ErrorCode.INTERNAL_ERROR, "对账店铺未写入")
        counts = _issue_counts(session, [run.id])
        created = _run_dict(
            run,
            store,
            version=None,
            issue_count=counts.get(run.id, 0),
            detail=True,
            session=session,
            permission_service=permission_service,
            principal=principal,
        )
        created["before"] = {}
        return created

    return cast(
        dict[str, Any],
        make_action_dispatcher(session, permission_service).dispatch(
            principal=principal,
            permission="integration:write",
            risk_tier="low",
            action="ReconRun.create",
            entity="ReconRun",
            entity_id=run_id,
            payload=payload_data,
            idempotency_key=idempotency_key,
            request_id=request_id,
            hooks={"idempotency_and_version": before_replay},
            business_action=business_action,
        ),
    )


def _apply_scope(
    statement: Select[Any],
    permission_service: PermissionService,
    principal: Principal,
) -> Select[Any]:
    scoped = apply_store_scope(
        statement,
        ReconRun.store_id,
        permission_service.store_scope(principal, "ReconRun"),
    )
    return cast(
        Select[Any],
        apply_period_scope(
            scoped,
            ReconRun.period,
            permission_service.period_scope(principal, "ReconRun"),
        ),
    )


def _ordering(sort: str | None) -> tuple[Any, ...]:
    if sort is None:
        return (ReconRun.started_at.desc(), ReconRun.id.desc())
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field not in _SORTS:
        raise APIError(
            ErrorCode.VALIDATION_FAILED,
            "sort 只支持 createdAt、period、matched、status、finishedAt",
        )
    column = _SORTS[field]
    return (
        column.desc() if descending else column.asc(),
        ReconRun.id.desc() if descending else ReconRun.id.asc(),
    )


def _versions(session: Session, run_ids: list[UUID]) -> dict[str, EntityVersion]:
    if not run_ids:
        return {}
    rows = session.scalars(
        select(EntityVersion)
        .where(
            EntityVersion.entity_type == "ReconRun",
            EntityVersion.entity_id.in_([str(run_id) for run_id in run_ids]),
        )
        .order_by(EntityVersion.version.asc())
    )
    found: dict[str, EntityVersion] = {}
    for row in rows:
        found[row.entity_id] = row
    return found


def _issue_counts(session: Session, run_ids: list[UUID]) -> dict[UUID, int]:
    if not run_ids:
        return {}
    counted = session.execute(
        select(Issue.recon_run_id, func.count())
        .where(Issue.recon_run_id.in_(run_ids))
        .group_by(Issue.recon_run_id)
    ).all()
    return {run_id: int(count) for run_id, count in counted if run_id is not None}


def _minor_units(amount: Decimal) -> int:
    return to_amount_minor(amount)


def _match_rate(run: ReconRun) -> str | None:
    if run.groups_total == 0:
        return None
    return format(Decimal(run.groups_matched) / Decimal(run.groups_total), "f")


def _provenance(run: ReconRun, version: EntityVersion | None) -> dict[str, Any]:
    if version is None:
        return {
            "actorType": "system",
            "actorId": run.created_by,
            "onBehalfOf": None,
            "actionId": "recon.run",
        }
    return {
        "actorType": version.actor_type,
        "actorId": None if version.actor_id is None else str(version.actor_id),
        "onBehalfOf": None if version.on_behalf_of is None else str(version.on_behalf_of),
        "actionId": version.action_id,
    }


def _run_dict(
    run: ReconRun,
    store: Store,
    *,
    version: EntityVersion | None,
    issue_count: int,
    detail: bool,
    session: Session,
    permission_service: PermissionService,
    principal: Principal,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(run.id),
        "storeId": str(run.store_id),
        "storeName": store.name,
        "period": run.period,
        "scope": {
            "storeId": str(run.store_id),
            "period": run.period,
            "asOf": run.as_of.isoformat(),
        },
        "matched": run.groups_matched,
        "unmatched": run.groups_total - run.groups_matched,
        "issues": issue_count,
        "groupsTotal": run.groups_total,
        "groupsMatched": run.groups_matched,
        "matchRate": _match_rate(run),
        "status": run.status,
        "nonOrderLines": run.non_order_lines,
        "ruleSetVersion": run.rule_set_version,
        "createdAt": run.started_at.isoformat(),
        "updatedAt": None if run.finished_at is None else run.finished_at.isoformat(),
        "finishedAt": None if run.finished_at is None else run.finished_at.isoformat(),
        "version": 0 if version is None else version.version,
        "provenance": _provenance(run, version),
    }
    if detail:
        payload["matches"] = [
            permission_service.serialize(
                principal,
                _match_dict(row, store.currency),
                {"diff": "sku.cost:read"},
            )
            for row in session.scalars(select(Match).where(Match.recon_run_id == run.id))
        ]
        payload["issueItems"] = [
            {
                "id": str(row.id),
                "kind": row.kind,
                "severity": row.severity,
                "status": row.status,
                "detail": row.detail_json,
            }
            for row in session.scalars(select(Issue).where(Issue.recon_run_id == run.id))
        ]
    return payload


def _match_dict(row: Match, currency: str) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "settlementLineId": None if row.settlement_line_id is None else str(row.settlement_line_id),
        "orderLineId": str(row.order_line_id),
        "ruleId": row.rule_id,
        "status": row.status,
        "diff": {"amountMinor": _minor_units(row.diff), "currency": currency},
        "matchedAt": row.matched_at.isoformat(),
    }


__all__ = [
    "ReconRunCreatePayload",
    "create_recon_run",
    "get_recon_run",
    "list_recon_runs",
    "scope_denied",
]
