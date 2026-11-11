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
    def submit(self, **_: Any) -> Any:
        raise NotImplementedError("审批网关由 audit-approval 块提供")

    def resolve(self, **_: Any) -> Any:
        raise NotImplementedError("审批网关由 audit-approval 块提供")


__all__ = ["ApprovalGateway", "ApprovalReason", "ApprovalResolution", "DefaultApprovalGateway"]
