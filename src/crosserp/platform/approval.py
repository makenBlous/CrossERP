"""审批网关协议; 具体审批人解析由 audit-approval 块实现。"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

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
        approval_type: str,
        request_id: str | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["ApprovalGateway", "ApprovalReason", "ApprovalResolution"]
