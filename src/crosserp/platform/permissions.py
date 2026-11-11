"""跨入口权限服务协议与旧权限矩阵桥接实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from crosserp.api.errors import APIError, ErrorCode
from crosserp.auth.permissions import has_permission
from crosserp.platform.principal import Principal


class PermissionDenied(APIError):
    def __init__(self, permission: str) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "无权执行该操作", details={"permission": permission})


class PermissionService(Protocol):
    def require(self, principal: Principal, permission: str, resource: Any = None) -> None: ...

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]: ...


class DefaultPermissionService:
    """临时桥接旧 15 点权限; iam 块可替换此实现而不改业务调用方。"""

    def require(self, principal: Principal, permission: str, resource: Any = None) -> None:
        if permission in {"public", "authenticated"}:
            if permission == "authenticated" and principal.user_id is None:
                raise PermissionDenied(permission)
            return
        if permission in principal.permissions:
            return
        try:
            allowed = has_permission(set(principal.roles), permission)
        except ValueError:
            allowed = False
        if not allowed:
            raise PermissionDenied(permission)

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]:
        if principal.data_scope is None:
            return {}
        if isinstance(principal.data_scope, Mapping):
            return dict(principal.data_scope)
        return {"scope": principal.data_scope}


__all__ = ["DefaultPermissionService", "PermissionDenied", "PermissionService"]
