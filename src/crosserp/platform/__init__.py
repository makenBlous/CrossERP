"""跨业务块共享的平台协议。"""

from crosserp.platform.approval import (
    ApprovalGateway,
    ApprovalReason,
    ApprovalResolution,
    DefaultApprovalGateway,
)
from crosserp.platform.audit import AuditRecorder, DefaultAuditRecorder
from crosserp.platform.dispatcher import (
    ActionDispatcher,
    AutonomyDecision,
    RiskTier,
    can_ai_execute,
)
from crosserp.platform.permissions import (
    DefaultPermissionService,
    PermissionDenied,
    PermissionService,
)
from crosserp.platform.principal import ActorType, Principal, get_principal

__all__ = [
    "ActionDispatcher",
    "ActorType",
    "ApprovalGateway",
    "ApprovalReason",
    "ApprovalResolution",
    "AuditRecorder",
    "AutonomyDecision",
    "DefaultApprovalGateway",
    "DefaultAuditRecorder",
    "DefaultPermissionService",
    "PermissionDenied",
    "PermissionService",
    "Principal",
    "RiskTier",
    "can_ai_execute",
    "get_principal",
]
