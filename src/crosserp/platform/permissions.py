"""统一权限服务协议与数据库 IAM 适配器。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from crosserp.api.errors import APIError, ErrorCode
from crosserp.iam.service import IAMService
from crosserp.platform.principal import Principal


class PermissionDenied(APIError):
    def __init__(self, permission: str) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "无权执行该操作", details={"permission": permission})


class PermissionService(Protocol):
    def require(self, principal: Principal, permission: str) -> None: ...

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]: ...


class DefaultPermissionService:
    """所有入口共用的数据库 IAM 适配器。"""

    def __init__(self, iam: IAMService) -> None:
        self.iam = iam

    def require(self, principal: Principal, permission: str) -> None:
        if permission == "public":
            return
        if permission == "authenticated" and principal.user_id is not None:
            return
        try:
            self.iam.require(principal, permission)
        except APIError as exc:
            if exc.code is ErrorCode.FORBIDDEN:
                raise PermissionDenied(permission) from exc
            raise

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]:
        return self.iam.data_scope_filter(principal, entity)


__all__ = ["DefaultPermissionService", "PermissionDenied", "PermissionService"]
