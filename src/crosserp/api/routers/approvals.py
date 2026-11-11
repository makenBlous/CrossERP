"""审批中心 API。"""
# ruff: noqa: B008

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import RootModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.metadata import api_endpoint
from crosserp.api.schemas import CamelModel
from crosserp.approval.gateway import ApprovalGatewayImpl, ApproverResolver
from crosserp.approval.state import ConcurrentModification
from crosserp.db.schema import Approval, ApprovalType, WorkflowRule
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.principal import Principal, get_principal

router = APIRouter()


class ApprovalDecisionBody(CamelModel):
    decision: Literal["approve", "reject"]
    comment: str = ""
    payload_hash: str | None = None


class InitiatorConfirmBody(RootModel[dict[str, Any]]):
    root: dict[str, Any]


class WorkflowRuleUpdateBody(CamelModel):
    steps: Any | None = None
    version: int | None = None


def _session(request: Request) -> Session:
    return Session(request.app.state.database_engine)


def _auth(principal: Principal, permission: str) -> None:
    from crosserp.platform.permissions import DefaultPermissionService

    DefaultPermissionService().require(principal, permission)


def _item(row: Approval) -> dict[str, Any]:
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
    return {"items": items, "page": page, "pageSize": page_size, "total": total}


@router.get("/approvals")
@api_endpoint(
    entity="Approval", action="Approval.list", permission="approval:read", risk_tier="none"
)
def list_approvals(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(principal, "approval:read")
    with _session(request) as session:
        stmt = select(Approval).order_by(Approval.requested_at.desc())
        all_rows = list(session.scalars(stmt))
        if q:
            filtered: list[Approval] = []
            for row in all_rows:
                assert row.resolution is not None
                if (
                    row.state == q
                    or row.resolution.get("mode") == q
                    or row.resolution.get("reason") == q
                ):
                    filtered.append(row)
            all_rows = filtered
        total = len(all_rows)
        rows = all_rows[(page - 1) * page_size : page * page_size]
        return _page([_item(row) for row in rows], page, page_size, int(total))


@router.get("/approvals/types")
@api_endpoint(
    entity="ApprovalType", action="ApprovalType.list", permission="approval:read", risk_tier="none"
)
def approval_types_early(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(principal, "approval:read")
    with _session(request) as session:
        rows = list(
            session.scalars(
                select(ApprovalType)
                .where(ApprovalType.enabled.is_(True))
                .order_by(ApprovalType.code)
            )
        )
        return _page(
            [
                {
                    "id": str(row.id),
                    "code": row.code,
                    "name": row.name,
                    "riskTier": row.risk_tier,
                    "template": row.template_json,
                }
                for row in rows
            ],
            page,
            page_size,
            len(rows),
        )


@router.get("/approvals/{id}")
@api_endpoint(
    entity="Approval", action="Approval.get", permission="approval:read", risk_tier="none"
)
def get_approval(
    id: str, request: Request, principal: Principal = Depends(get_principal)
) -> dict[str, Any]:
    _auth(principal, "approval:read")
    with _session(request) as session:
        try:
            row = session.get(Approval, UUID(id))
        except ValueError:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
        return _item(row)


@router.post("/approvals/{id}/decide")
@api_endpoint(
    entity="Approval", action="Approval.decide", permission="approval:approve", risk_tier="critical"
)
def decide_approval(
    id: str,
    request: Request,
    body: ApprovalDecisionBody,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(principal, "approval:approve")
    try:
        approval_id = UUID(id)
    except ValueError:
        raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
    with _session(request) as session, session.begin():
        try:
            row = ApprovalGatewayImpl(session).decide(
                approval_id,
                principal=principal,
                decision=body.decision,
                comment=body.comment,
                content_hash=body.payload_hash,
                request_id=request.state.request_id,
            )
        except ConcurrentModification as exc:
            raise APIError(ErrorCode.CONFLICT_VERSION, str(exc)) from exc
        return {"approval": _item(row), "status": row.state}


@router.post("/approvals/{id}/withdraw")
@api_endpoint(
    entity="Approval",
    action="Approval.withdraw",
    permission="approval:create",
    risk_tier="critical",
)
def withdraw_approval(
    id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(principal, "approval:create")
    try:
        approval_id = UUID(id)
    except ValueError:
        raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
    with _session(request) as session, session.begin():
        row = ApprovalGatewayImpl(session).withdraw(
            approval_id,
            principal=principal,
            request_id=request.state.request_id,
        )
        return {"approval": _item(row), "status": row.state}


@router.post("/approvals/{id}/initiator-confirm")
@api_endpoint(
    entity="Approval",
    action="Approval.initiator_confirm",
    permission="approval:create",
    risk_tier="critical",
)
def initiator_confirm(
    id: str,
    request: Request,
    body: InitiatorConfirmBody,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(principal, "approval:create")
    try:
        approval_id = UUID(id)
    except ValueError:
        raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
    with _session(request) as session, session.begin():
        row = ApprovalGatewayImpl(session).initiator_confirm(
            approval_id,
            principal=principal,
            content=body.root,
            request_id=request.state.request_id,
        )
        return {"approval": _item(row), "status": row.state}


@router.get("/workflow/rules/resolve")
@api_endpoint(
    entity="WorkflowRule",
    action="WorkflowRule.read_resolve",
    permission="approval:read",
    risk_tier="none",
)
def resolve_rule(
    request: Request,
    principal: Principal = Depends(get_principal),
    approval_type: str = Query("default", alias="approvalType"),
    target_type: str | None = Query(None, alias="targetType"),
    target_id: str | None = Query(None, alias="targetId"),
) -> dict[str, Any]:
    _auth(principal, "approval:read")
    with _session(request) as session:
        result = ApproverResolver(session).resolve(
            approval_type, principal.user_id, principal.on_behalf_of
        )
        if result["approvers"]:
            return {
                "mode": "approver",
                "approvers": result["approvers"],
                "note": "等待审批人审批",
                "ruleVersion": result["ruleVersion"],
                "snapshot": result["snapshot"],
            }
        return {
            "mode": "no_approver_auto",
            "approvers": [],
            "note": f"提交即生效 ({result['reason'] or 'no_account'})",
            "ruleVersion": result["ruleVersion"],
            "snapshot": result["snapshot"],
        }


@router.get("/workflow/rules")
@api_endpoint(
    entity="WorkflowRule", action="WorkflowRule.list", permission="approval:read", risk_tier="none"
)
def workflow_rules(
    request: Request,
    principal: Principal = Depends(get_principal),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=200),
    q: str | None = None,
) -> dict[str, Any]:
    _auth(principal, "approval:read")
    with _session(request) as session:
        rows = list(
            session.scalars(
                select(WorkflowRule).order_by(
                    WorkflowRule.approval_type, WorkflowRule.version.desc()
                )
            )
        )
        return _page(
            [
                {
                    "id": str(row.id),
                    "approvalType": row.approval_type,
                    "version": row.version,
                    "steps": row.steps_json,
                    "enabled": row.enabled,
                }
                for row in rows
            ],
            page,
            page_size,
            len(rows),
        )


@router.put("/workflow/rules/{id}")
@api_endpoint(
    entity="WorkflowRule",
    action="WorkflowRule.update",
    permission="approval:write",
    risk_tier="critical",
)
def update_workflow_rule(
    id: str,
    request: Request,
    body: WorkflowRuleUpdateBody,
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    _auth(principal, "approval:write")
    if principal.is_agent:
        raise APIError(ErrorCode.AI_AUTONOMY_CAPPED, "仅真人可修改审批规则")
    try:
        rule_id = UUID(id)
    except ValueError:
        raise APIError(ErrorCode.NOT_FOUND, "资源不存在") from None
    with _session(request) as session, session.begin():
        row = session.get(WorkflowRule, rule_id)
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "资源不存在")

        row.steps_json = row.steps_json if body.steps is None else body.steps
        row.version = row.version + 1 if body.version is None else body.version
        row.updated_by = principal.user_id
        row.updated_at = datetime.now(UTC)
        DefaultAuditRecorder(session).record(
            principal=principal,
            entity="WorkflowRule",
            action="WorkflowRule.update",
            diff={"steps": row.steps_json},
            request_id=request.state.request_id,
        )
        return {
            "id": str(row.id),
            "approvalType": row.approval_type,
            "version": row.version,
            "steps": row.steps_json,
        }
