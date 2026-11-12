"""审批网关协议; 具体审批人解析由 audit-approval 块实现。"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ApprovalSubmission:
    """审批提交的唯一返回值。HTTP 和审计都使用 to_payload()。"""

    approval_id: UUID
    state: str
    resolution: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "approvalId": str(self.approval_id),
            "status": self.state,
            "state": self.state,
            "resolution": self.resolution,
        }


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
    ) -> ApprovalSubmission: ...


__all__ = [
    "ApprovalGateway",
    "ApprovalReason",
    "ApprovalResolution",
    "ApprovalSubmission",
]
