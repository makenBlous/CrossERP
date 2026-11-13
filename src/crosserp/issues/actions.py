"""对账异常的 JSON 动作。计算复用既有异常服务和总账草稿出口。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, StrictInt, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import CamelModel
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.audit.context import AuditContext
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.core.enums import IssueStatus
from crosserp.core.money import to_amount_minor
from crosserp.db.repo.issues import detail_of
from crosserp.db.schema import (
    EntityVersion,
    Issue,
    OrderLine,
    ReconRun,
    Settlement,
    SettlementLine,
    Store,
    Voucher,
)
from crosserp.iam.scope import AllStores, store_contains
from crosserp.issues.catalog import render
from crosserp.issues.service import transition
from crosserp.ledger.write_service import write_issue_adjustment_draft
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal

_SORT_FIELDS = {
    "createdAt": Issue.created_at,
    "status": Issue.status,
    "kind": Issue.kind,
    "severity": Issue.severity,
}
_AMOUNT_KEYS = ("diff", "overcharge", "amount")


class ResolvePayload(CamelModel):
    resolution: IssueStatus
    reason: str = Field(min_length=5, max_length=2000)
    expected_version: StrictInt = Field(ge=0)

    @field_validator("resolution")
    @classmethod
    def only_explained_or_ignored(cls, value: IssueStatus) -> IssueStatus:
        if value not in {IssueStatus.EXPLAINED, IssueStatus.IGNORED}:
            raise ValueError("resolution 只能是 explained 或 ignored")
        return value


class DraftVoucherPayload(CamelModel):
    expected_version: StrictInt = Field(ge=0)
    reason: str | None = Field(default=None, max_length=2000)


def list_recon_issues(
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
    rows = _visible_issues(session, principal, permission_service)
    if q:
        needle = q.casefold()
        rows = [row for row in rows if needle in _search_text(session, row)]
    rows = _sorted(rows, sort)
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    versions = _versions(session, [str(row.id) for row in page_rows])
    return {
        "items": [
            permission_service.serialize(
                principal,
                _issue_dict(session, row, versions.get(str(row.id), 0)),
                {"amount": "sku.cost:read"},
            )
            for row in page_rows
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def get_recon_issue(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    issue_id: UUID,
) -> dict[str, Any]:
    permission_service.require(principal, "report:read")
    issue = session.get(Issue, issue_id)
    if issue is None or not _in_scope(session, principal, permission_service, issue):
        raise not_found()
    versions = _versions(session, [str(issue.id)])
    return permission_service.serialize(
        principal,
        _issue_dict(session, issue, versions.get(str(issue.id), 0)),
        {"amount": "sku.cost:read"},
    )


def resolve_issue(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    issue_id: UUID,
    payload: ResolvePayload,
    idempotency_key: str,
    request_id: str | None,
) -> dict[str, Any]:
    _visible_for_write(session, principal, permission_service, issue_id, "integration:write")
    payload_data = payload.model_dump(by_alias=True, mode="json")

    def business_action() -> dict[str, Any]:
        issue = session.get(Issue, issue_id)
        if issue is None:
            raise not_found()
        before = _snapshot(session, issue)
        try:
            transition(
                session,
                issue_id,
                payload.resolution,
                payload.reason,
                AuditContext(
                    actor_type="agent" if principal.is_agent else "user",
                    actor_user_id=principal.user_id,
                    request_id=request_id,
                ),
            )
        except LookupError as exc:
            raise not_found() from exc
        except ValueError as exc:
            raise APIError(ErrorCode.ILLEGAL_TRANSITION, str(exc), status_code=409) from exc
        after = _snapshot(session, issue)
        undo = {
            "action": "ReconIssue.resolve",
            "entity": "ReconIssue",
            "id": str(issue_id),
            "previous": before,
        }
        after["undo"] = undo
        return {
            "id": str(issue.id),
            "status": issue.status,
            "resolutionNote": issue.resolution_note,
            "amount": after["amount"],
            "before": before,
            "after": after,
            "undo": undo,
        }

    return _dispatch(
        session,
        principal=principal,
        permission_service=permission_service,
        permission="integration:write",
        risk_tier="medium",
        action="ReconIssue.resolve",
        issue_id=issue_id,
        payload=payload_data,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key,
        request_id=request_id,
        business_action=business_action,
    )


def draft_voucher_from_issue(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    issue_id: UUID,
    payload: DraftVoucherPayload,
    idempotency_key: str,
    request_id: str | None,
) -> dict[str, Any]:
    _visible_for_write(session, principal, permission_service, issue_id, "journal_entry:create")
    payload_data = payload.model_dump(by_alias=True, mode="json")

    def business_action() -> dict[str, Any]:
        issue = session.get(Issue, issue_id)
        if issue is None:
            raise not_found()
        before = _snapshot(session, issue)
        approval = ApprovalGatewayImpl(session).submit(
            principal=principal,
            entity="ReconIssue",
            action="ReconIssue.draft_voucher",
            payload=payload_data,
            risk_tier="high",
            approval_type="reconissue",
            request_id=request_id,
        )
        if approval.state != "auto_effective":
            return {
                "id": str(issue.id),
                "status": approval.state,
                "approvalId": str(approval.approval_id),
                "before": before,
                "after": before,
            }
        voucher = _write_draft(session, issue, principal)
        after = {**before, "voucherId": str(voucher.id)}
        return {
            "id": str(voucher.id),
            "status": voucher.state,
            "issueId": str(issue.id),
            "approvalId": str(approval.approval_id),
            "amount": _money_payload(voucher.total_debit, voucher.currency),
            "before": before,
            "after": after,
        }

    return _dispatch(
        session,
        principal=principal,
        permission_service=permission_service,
        permission="journal_entry:create",
        risk_tier="high",
        action="ReconIssue.draft_voucher",
        issue_id=issue_id,
        payload=payload_data,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key,
        request_id=request_id,
        business_action=business_action,
    )


def _dispatch(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    permission: str,
    risk_tier: str,
    action: str,
    issue_id: UUID,
    payload: dict[str, Any],
    expected_version: int,
    idempotency_key: str,
    request_id: str | None,
    business_action: Any,
) -> dict[str, Any]:
    result = make_action_dispatcher(
        session, permission_service, undo_restore=CATALOG_UNDO_RESTORE
    ).dispatch(
        principal=principal,
        permission=permission,
        risk_tier=risk_tier,
        action=action,
        entity="ReconIssue",
        entity_id=issue_id,
        payload=payload,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
        request_id=request_id,
        business_action=business_action,
    )
    if not isinstance(result, dict):
        raise APIError(ErrorCode.INTERNAL_ERROR, "动作结果必须是对象")
    return result


def _visible_for_write(
    session: Session,
    principal: Principal,
    permission_service: PermissionService,
    issue_id: UUID,
    permission: str,
) -> Issue:
    permission_service.require(principal, permission)
    issue = session.get(Issue, issue_id)
    if issue is None:
        raise not_found()
    if not _in_scope(session, principal, permission_service, issue):
        raise APIError(ErrorCode.DATA_SCOPE_DENIED, "数据范围不足")
    return issue


def _write_draft(session: Session, issue: Issue, principal: Principal) -> Voucher:
    store_id = store_id_of(session, issue)
    period = period_of(session, issue)
    money = money_of(session, issue)
    if store_id is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "异常没有店铺，不能生成调整凭证")  # noqa: RUF001
    if period is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "异常没有期间，不能生成调整凭证")  # noqa: RUF001
    if money is None:
        raise APIError(ErrorCode.VALIDATION_FAILED, "异常没有金额，不能生成调整凭证")  # noqa: RUF001
    if principal.user_id is None:
        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    try:
        return write_issue_adjustment_draft(
            session,
            issue_id=issue.id,
            store_id=store_id,
            period=period,
            amount=_decimal_amount(session, issue),
            currency=str(money["currency"]),
            created_by=str(principal.user_id),
        )
    except ValueError as exc:
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, str(exc), status_code=409) from exc


def _visible_issues(
    session: Session, principal: Principal, permission_service: PermissionService
) -> list[Issue]:
    rows = list(session.scalars(select(Issue)))
    return [row for row in rows if _in_scope(session, principal, permission_service, row)]


def _in_scope(
    session: Session,
    principal: Principal,
    permission_service: PermissionService,
    issue: Issue,
) -> bool:
    scope = permission_service.store_scope(principal, "ReconIssue")
    store_id = store_id_of(session, issue)
    if store_id is None:
        return isinstance(scope, AllStores)
    return store_contains(scope, store_id)


def _sorted(rows: list[Issue], sort: str | None) -> list[Issue]:
    selected = "-createdAt" if sort is None else sort
    descending = selected.startswith("-")
    field = selected[1:] if descending else selected
    if field not in _SORT_FIELDS:
        raise APIError(ErrorCode.VALIDATION_FAILED, "sort 只支持 createdAt、status、kind、severity")
    return sorted(
        rows,
        key=lambda row: (_sort_value(row, field), str(row.id)),
        reverse=descending,
    )


def _sort_value(issue: Issue, field: str) -> str:
    if field == "createdAt":
        return issue.created_at.isoformat()
    if field == "status":
        return issue.status
    if field == "kind":
        return issue.kind
    return issue.severity


def _search_text(session: Session, issue: Issue) -> str:
    detail = detail_of(issue)
    parts = [issue.kind, issue.status, issue.resolution_note or "", render(issue)]
    for key in ("source_ref", "order_id", "sku", "period"):
        if key in detail and isinstance(detail[key], str):
            parts.append(detail[key])
    store_id = store_id_of(session, issue)
    if store_id is not None:
        store = session.get(Store, store_id)
        if store is not None:
            parts.append(store.name)
    return " ".join(parts).casefold()


def _issue_dict(session: Session, issue: Issue, version: int) -> dict[str, Any]:
    detail = detail_of(issue)
    store_id = store_id_of(session, issue)
    return {
        "id": str(issue.id),
        "kind": issue.kind,
        "severity": issue.severity,
        "status": issue.status,
        "storeId": None if store_id is None else str(store_id),
        "amount": money_of(session, issue),
        "resolutionNote": issue.resolution_note,
        "summary": render(issue),
        "version": version,
        "createdAt": _iso(issue.created_at),
        "reconRunId": None if issue.recon_run_id is None else str(issue.recon_run_id),
        "provenance": {
            "batchId": detail.get("import_batch_id"),
            "sourceFile": detail.get("source_file"),
            "rowNo": detail.get("row_no"),
        },
    }


def _snapshot(session: Session, issue: Issue) -> dict[str, Any]:
    return {
        "id": str(issue.id),
        "status": issue.status,
        "resolutionNote": issue.resolution_note,
        "kind": issue.kind,
        "amount": money_of(session, issue),
    }


def _versions(session: Session, entity_ids: list[str]) -> dict[str, int]:
    if not entity_ids:
        return {}
    rows = session.execute(
        select(EntityVersion.entity_id, func.max(EntityVersion.version))
        .where(
            EntityVersion.entity_type == "ReconIssue",
            EntityVersion.entity_id.in_(entity_ids),
        )
        .group_by(EntityVersion.entity_id)
    )
    return {str(entity_id): int(version) for entity_id, version in rows}


def store_id_of(session: Session, issue: Issue) -> UUID | None:
    detail = detail_of(issue)
    if "store_id" in detail and isinstance(detail["store_id"], str) and detail["store_id"]:
        return UUID(detail["store_id"])
    if issue.recon_run_id is not None:
        run = session.get(ReconRun, issue.recon_run_id)
        if run is not None:
            return run.store_id
    if issue.order_line_id is not None:
        order = session.get(OrderLine, issue.order_line_id)
        if order is not None:
            return order.store_id
    if issue.settlement_line_id is not None:
        line = session.get(SettlementLine, issue.settlement_line_id)
        if line is not None:
            settlement = session.get(Settlement, line.settlement_id)
            if settlement is not None:
                return settlement.store_id
    return None


def period_of(session: Session, issue: Issue) -> str | None:
    detail = detail_of(issue)
    if "period" in detail and isinstance(detail["period"], str) and len(detail["period"]) == 7:
        return detail["period"]
    if issue.recon_run_id is not None:
        run = session.get(ReconRun, issue.recon_run_id)
        if run is not None:
            return run.period
    return None


def money_of(session: Session, issue: Issue) -> dict[str, Any] | None:
    currency = currency_of(session, issue)
    if currency is None:
        return None
    return _money_payload(_decimal_amount(session, issue), currency)


def currency_of(session: Session, issue: Issue) -> str | None:
    if issue.settlement_line_id is not None:
        line = session.get(SettlementLine, issue.settlement_line_id)
        if line is not None:
            settlement = session.get(Settlement, line.settlement_id)
            if settlement is not None:
                return settlement.currency
    if issue.order_line_id is not None:
        order = session.get(OrderLine, issue.order_line_id)
        if order is not None:
            return order.currency
    store_id = store_id_of(session, issue)
    if store_id is not None:
        store = session.get(Store, store_id)
        if store is not None:
            return store.currency
    return None


def _decimal_amount(session: Session, issue: Issue) -> Decimal:
    detail = detail_of(issue)
    for key in _AMOUNT_KEYS:
        if key in detail:
            value = detail[key]
            if isinstance(value, float):
                raise TypeError("金额不能是 float")
            return Decimal(str(value))
    if issue.settlement_line_id is not None:
        line = session.get(SettlementLine, issue.settlement_line_id)
        if line is not None:
            return line.amount
    if issue.order_line_id is not None:
        order = session.get(OrderLine, issue.order_line_id)
        if order is not None and order.item_price is not None:
            return order.item_price
    return Decimal(0)


def _money_payload(amount: Decimal, currency: str) -> dict[str, Any]:
    return {"amountMinor": to_amount_minor(amount), "currency": currency}


def _iso(value: datetime) -> str:
    return value.isoformat()


__all__ = [
    "DraftVoucherPayload",
    "ResolvePayload",
    "draft_voucher_from_issue",
    "get_recon_issue",
    "list_recon_issues",
    "resolve_issue",
]
