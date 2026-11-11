"""审批网关协议; 具体审批人解析由 audit-approval 块实现。"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from crosserp.platform.principal import Principal


class ApprovalResolution(StrEnum):
    REQUIRED = "required"
    AUTO_EFFECTIVE = "auto_effective"
    AWAITING_INITIATOR = "awaiting_initiator"


class ApprovalReason(StrEnum):
    NO_RULE = "no_rule"
    NO_ACCOUNT = "no_account"
    ONLY_SELF = "only_self"


class ApprovalGateway(Protocol):
    def submit(
        self,
        *,
        principal: Principal,
        entity: str,
        action: str,
        payload: Any,
        risk_tier: str,
    ) -> Any: ...

    def resolve(
        self,
        *,
        approval_id: UUID,
        principal: Principal,
        decision: str,
        comment: str | None = None,
    ) -> Any: ...


class DefaultApprovalGateway:
    """底座兼容入口, 实际委托给 P0-03a 网关。"""

    def __init__(self, session: Any) -> None:
        self._session = session

    def submit(self, **kwargs: Any) -> Any:
        from crosserp.approval.gateway import ApprovalGatewayImpl

        return ApprovalGatewayImpl(self._session).submit(**kwargs)

    def resolve(
        self, *, approval_id: UUID, principal: Principal, decision: str, comment: str | None = None
    ) -> Any:
        from crosserp.approval.gateway import ApprovalGatewayImpl

        return ApprovalGatewayImpl(self._session).decide(
            approval_id, principal=principal, decision=decision, comment=comment or ""
        )


def gateway_for(session: Any) -> Any:
    """返回 P0-03a 的真实审批网关, 保留底座导入路径。"""
    from crosserp.approval.gateway import ApprovalGatewayImpl

    return ApprovalGatewayImpl(session)


__all__ = [
    "ApprovalGateway",
    "ApprovalReason",
    "ApprovalResolution",
    "DefaultApprovalGateway",
    "gateway_for",
]
