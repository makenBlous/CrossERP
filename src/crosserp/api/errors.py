"""JSON API 统一错误。"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    CSRF_INVALID = "CSRF_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FORBIDDEN = "FORBIDDEN"
    DATA_SCOPE_DENIED = "DATA_SCOPE_DENIED"
    FIELD_FORBIDDEN = "FIELD_FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT_VERSION = "CONFLICT_VERSION"
    IDEMPOTENCY_REPLAY_MISMATCH = "IDEMPOTENCY_REPLAY_MISMATCH"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    SOD_VIOLATION = "SOD_VIOLATION"
    SELF_APPROVAL_FORBIDDEN = "SELF_APPROVAL_FORBIDDEN"
    PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
    AMOUNT_LIMIT_EXCEEDED = "AMOUNT_LIMIT_EXCEEDED"
    PERIOD_CLOSED = "PERIOD_CLOSED"
    LEDGER_UNBALANCED = "LEDGER_UNBALANCED"
    PLACEHOLDER_ACCOUNT_CODE = "PLACEHOLDER_ACCOUNT_CODE"
    UNVERIFIED_RULE_VERSION = "UNVERIFIED_RULE_VERSION"
    AI_MODE_OFF = "AI_MODE_OFF"
    AI_AUTONOMY_CAPPED = "AI_AUTONOMY_CAPPED"
    AI_INITIATOR_MISMATCH = "AI_INITIATOR_MISMATCH"
    RISK_BLOCKED = "RISK_BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    MODULE_DISABLED = "MODULE_DISABLED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    DELEGATION_INVALID = "DELEGATION_INVALID"
    DELEGATION_SCOPE_EXCEEDED = "DELEGATION_SCOPE_EXCEEDED"
    PERMISSIONS_CHANGED = "PERMISSIONS_CHANGED"
    SCENARIO_READ_ONLY = "SCENARIO_READ_ONLY"
    INTERNAL = "INTERNAL"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_STATUS: dict[ErrorCode, int] = {
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.SESSION_EXPIRED: 401,
    ErrorCode.PERMISSION_DENIED: 404,
    ErrorCode.FORBIDDEN: 404,
    ErrorCode.DATA_SCOPE_DENIED: 404,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.CONFLICT_VERSION: 409,
    ErrorCode.IDEMPOTENCY_REPLAY_MISMATCH: 409,
    ErrorCode.IDEMPOTENCY_CONFLICT: 409,
    ErrorCode.APPROVAL_REQUIRED: 409,
    ErrorCode.RISK_BLOCKED: 403,
    ErrorCode.AI_AUTONOMY_CAPPED: 403,
    ErrorCode.DELEGATION_SCOPE_EXCEEDED: 404,
    ErrorCode.PERMISSIONS_CHANGED: 404,
    ErrorCode.INTERNAL: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


class APIError(Exception):
    """可安全返回给客户端的 API 异常, 不包含堆栈。"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code or _STATUS.get(code, 400)


def error_payload(
    code: ErrorCode, message: str, request_id: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "code": code.value,
        "message": message,
        "details": details or {},
        "requestId": request_id,
    }


def not_found(*, request_id: str | None = None, message: str = "资源不存在") -> APIError:
    """无权与不存在共用 404 约定, 避免泄露资源存在性。"""
    return APIError(ErrorCode.NOT_FOUND, message, status_code=404)


__all__ = ["APIError", "ErrorCode", "error_payload", "not_found"]
