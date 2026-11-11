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
    def require(self, principal: Principal, permission: str, resource: Any = None) -> None: ...

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]: ...

    def current_permissions(self, principal: Principal) -> frozenset[str]: ...


class DefaultPermissionService:
    """所有入口共用的数据库 IAM 适配器。"""

    def __init__(self, iam: IAMService | None = None) -> None:
        self.iam = iam

    def bind(self, iam: IAMService) -> None:
        self.iam = iam

    def require(self, principal: Principal, permission: str, resource: Any = None) -> None:
        if permission == "public":
            return
        if permission == "authenticated" and principal.user_id is not None:
            return
        if self.iam is None:
            raise RuntimeError("权限服务尚未绑定 IAM 数据库")
        try:
            self.iam.require(principal, permission)
        except APIError as exc:
            if exc.code is ErrorCode.FORBIDDEN:
                raise PermissionDenied(permission) from exc
            raise

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]:
        if self.iam is None:
            raise RuntimeError("权限服务尚未绑定 IAM 数据库")
        return self.iam.data_scope_filter(principal, entity)

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        """返回本次动作应使用的被代表人权限快照。"""
        if principal.represented_permissions is not None:
            return principal.represented_permissions
        return principal.permissions


__all__ = ["DefaultPermissionService", "PermissionDenied", "PermissionService"]
