"""科目表与月汇率的查询、新增。"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, cast
from uuid import uuid4

from pydantic import Field, StrictInt, field_validator
from sqlalchemy import func, select
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.schemas import CamelModel
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.core.currency import require_iso_4217
from crosserp.core.errors import PrecisionError
from crosserp.db.repo.fx import get_fx_rate, upsert_fx_rate
from crosserp.db.schema import EntityVersion, FxRate
from crosserp.db.types import FxRate as FxRateColumn
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal
from crosserp.vouchers.accounts import (
    AccountMapping,
    is_placeholder_code,
    read_account_chart,
)

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_ACCOUNT_SORTS = ("accountKey", "code", "nameZh", "direction", "placeholder")
_FX_SORTS = ("period", "fromCcy", "toCcy", "rate", "source")


class _RateDialect:
    name = "mysql"


class FxRateCreatePayload(CamelModel):
    period: str
    from_ccy: str
    to_ccy: str
    rate: str
    source: str = Field(min_length=1, max_length=128)
    expected_version: StrictInt | None = Field(default=None, ge=0)

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        if _PERIOD_RE.fullmatch(value) is None:
            raise ValueError("期间必须是 YYYY-MM")
        return value

    @field_validator("from_ccy", "to_ccy", mode="before")
    @classmethod
    def validate_currency(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("币种必须是 ISO 4217 代码")
        return require_iso_4217(value)

    @field_validator("rate", mode="before")
    @classmethod
    def validate_rate(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("汇率必须是十进制字符串")
        return _rate_text(value)


def list_accounts(
    *,
    principal: Principal,
    permission_service: PermissionService,
    page: int,
    page_size: int,
    q: str | None,
    sort: str | None,
) -> dict[str, Any]:
    permission_service.require(principal, "report:read")
    try:
        accounts, _digest = read_account_chart()
    except FileNotFoundError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, str(exc)) from exc
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, str(exc)) from exc
    rows = [_account_item(key, mapping) for key, mapping in accounts.items()]
    if q:
        needle = q.casefold()
        rows = [
            row
            for row in rows
            if needle in str(row["accountKey"]).casefold()
            or needle in str(row["code"]).casefold()
            or needle in str(row["nameZh"]).casefold()
        ]
    rows = _sort_rows(rows, sort, _ACCOUNT_SORTS)
    return _page(rows, page, page_size)


def list_fx_rates(
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
    statement = select(FxRate)
    if q:
        needle = f"%{q}%"
        statement = statement.where(
            FxRate.period.ilike(needle)
            | FxRate.from_ccy.ilike(needle)
            | FxRate.to_ccy.ilike(needle)
            | FxRate.source.ilike(needle)
        )
    total = cast(int, session.scalar(select(func.count()).select_from(statement.subquery())))
    column, descending = _fx_order(sort)
    ordering = column.desc() if descending else column.asc()
    id_order = FxRate.id.desc() if descending else FxRate.id.asc()
    selected = list(
        session.scalars(
            statement.order_by(ordering, id_order).offset((page - 1) * page_size).limit(page_size)
        )
    )
    versions = _versions(session, [str(row.id) for row in selected])
    return {
        "items": [_fx_item(row, versions.get(str(row.id), 0)) for row in selected],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def create_fx_rate(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    payload: FxRateCreatePayload,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    existing = get_fx_rate(session, payload.period, payload.from_ccy, payload.to_ccy)
    entity_id = existing.id if existing is not None else uuid4()
    payload_data = payload.model_dump(by_alias=True, mode="json")
    rate = Decimal(payload.rate)

    def business_action() -> dict[str, Any]:
        if existing is not None and payload.expected_version is None:
            raise APIError(ErrorCode.VALIDATION_FAILED, "更新已有汇率必须提供 expectedVersion")
        approval = ApprovalGatewayImpl(session).submit(
            principal=principal,
            entity="FxRate",
            action="FxRate.create",
            payload=payload_data,
            risk_tier="high",
            approval_type="fxrate",
            request_id=request_id,
        )
        if approval.state != "auto_effective":
            return _approval_body(approval, applied=False)
        upsert_fx_rate(
            session,
            rate_id=entity_id,
            period=payload.period,
            from_ccy=payload.from_ccy,
            to_ccy=payload.to_ccy,
            rate=rate,
            source=payload.source,
        )
        if existing is not None:
            session.expire(existing)
        row = get_fx_rate(session, payload.period, payload.from_ccy, payload.to_ccy)
        if row is None:
            raise APIError(ErrorCode.INTERNAL_ERROR, "汇率写入后无法读回")
        body = _fx_item(row, 0)
        body.update(_approval_body(approval, applied=True))
        return body

    result = make_action_dispatcher(session, permission_service).dispatch(
        principal=principal,
        permission="integration:write",
        risk_tier="high",
        action="FxRate.create",
        entity="FxRate",
        entity_id=entity_id,
        payload=payload_data,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key,
        request_id=request_id,
        business_action=business_action,
    )
    return _present(result)


def _present(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise APIError(ErrorCode.INTERNAL_ERROR, "汇率动作结果无法序列化")
    if "applied" not in result and "state" in result:
        return {**result, "applied": result["state"] == "auto_effective"}
    return result


def _approval_body(approval: Any, *, applied: bool) -> dict[str, Any]:
    return {
        "approvalId": str(approval.id),
        "state": approval.state,
        "applied": applied,
    }


def _account_item(key: str, mapping: AccountMapping) -> dict[str, Any]:
    return {
        "accountKey": key,
        "code": mapping.code,
        "nameZh": mapping.name,
        "direction": mapping.direction,
        "placeholder": is_placeholder_code(mapping.code),
    }


def _fx_item(row: FxRate, version: int) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "period": row.period,
        "fromCcy": row.from_ccy,
        "toCcy": row.to_ccy,
        "rate": format(row.rate, "f"),
        "source": row.source,
        "grain": "month",
        "version": version,
    }


def _versions(session: Session, entity_ids: list[str]) -> dict[str, int]:
    if not entity_ids:
        return {}
    rows = session.execute(
        select(EntityVersion.entity_id, func.max(EntityVersion.version))
        .where(EntityVersion.entity_type == "FxRate", EntityVersion.entity_id.in_(entity_ids))
        .group_by(EntityVersion.entity_id)
    ).all()
    return {str(entity_id): int(version) for entity_id, version in rows}


def _page(rows: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    start = (page - 1) * page_size
    return {
        "items": rows[start : start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": len(rows),
    }


def _sort_rows(
    rows: list[dict[str, Any]], sort: str | None, allowed: tuple[str, ...]
) -> list[dict[str, Any]]:
    field, descending = _sort_field(sort, allowed)
    return sorted(rows, key=lambda row: (row[field], str(row["accountKey"])), reverse=descending)


def _sort_field(sort: str | None, allowed: tuple[str, ...]) -> tuple[str, bool]:
    if sort is None:
        return allowed[0], False
    descending = sort.startswith("-")
    name = sort[1:] if descending else sort
    if name not in allowed:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"sort 只支持 {', '.join(allowed)}")
    return name, descending


def _fx_order(sort: str | None) -> tuple[Any, bool]:
    field, descending = _sort_field(sort, _FX_SORTS)
    column = {
        "period": FxRate.period,
        "fromCcy": FxRate.from_ccy,
        "toCcy": FxRate.to_ccy,
        "rate": FxRate.rate,
        "source": FxRate.source,
    }[field]
    return column, descending


def _rate_text(value: str) -> str:
    try:
        rate = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("汇率必须是十进制字符串") from exc
    if not rate.is_finite():
        raise ValueError("汇率必须是十进制字符串")
    try:
        FxRateColumn().process_bind_param(rate, cast(Dialect, _RateDialect()))
    except (PrecisionError, TypeError) as exc:
        raise ValueError(str(exc)) from exc
    if rate <= 0:
        raise ValueError("汇率必须是正数")
    return format(rate, "f")


__all__ = [
    "FxRateCreatePayload",
    "create_fx_rate",
    "list_accounts",
    "list_fx_rates",
]
