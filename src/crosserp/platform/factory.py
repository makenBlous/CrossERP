"""为当前请求构造绑定同一事务的动作执行器。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.dispatcher import ActionDispatcher
from crosserp.platform.permissions import PermissionService


def make_action_dispatcher(
    session: Session, permission_service: PermissionService
) -> ActionDispatcher:
    """把动作执行器、审批网关和审计记录器绑定到请求会话。"""
    return ActionDispatcher(
        session=session,
        permission_service=permission_service,
        approval_gateway=ApprovalGatewayImpl(session),
        audit_recorder=DefaultAuditRecorder(session),
    )


__all__ = ["make_action_dispatcher"]
