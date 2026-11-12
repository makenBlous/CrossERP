"""统一权限服务协议与数据库 IAM 适配器。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

from fastapi import Request

from crosserp.api.errors import APIError, ErrorCode
from crosserp.iam.scope import StoreScope
from crosserp.iam.service import IAMService
from crosserp.platform.principal import Principal


class PermissionDenied(APIError):
    def __init__(self, permission: str) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "无权执行该操作", details={"permission": permission})


class PermissionService(Protocol):
    def require(self, principal: Principal, permission: str, resource: Any = None) -> None: ...

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]: ...

    def store_scope(self, principal: Principal, entity: str) -> StoreScope: ...

    def serialize(
        self, principal: Principal, record: dict[str, Any], field_permissions: dict[str, str]
    ) -> dict[str, Any]: ...

    def current_permissions(self, principal: Principal) -> frozenset[str]: ...


class DefaultPermissionService:
    """所有入口共用的数据库 IAM 适配器。"""

    def __init__(self, iam: IAMService | None = None) -> None:
        self.iam = iam

    def bind(self, iam: IAMService) -> None:
        self.iam = iam

    def require(self, principal: Principal, permission: str, resource: Any = None) -> None:
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
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
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
        return self.iam.data_scope_filter(principal, entity)

    def store_scope(self, principal: Principal, entity: str) -> StoreScope:
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
        return self.iam.store_scope(principal, entity)

    def serialize(
        self, principal: Principal, record: dict[str, Any], field_permissions: dict[str, str]
    ) -> dict[str, Any]:
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
        user_id = principal.effective_user_id
        if user_id is None:
            raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
        return self.iam.serialize(user_id, record, field_permissions)

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        """返回本次动作应使用的被代表人权限快照。"""
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
        permissions = self.iam.current_permissions(principal)
        if principal.represented_permissions is not None:
            permissions &= principal.represented_permissions
        return permissions


def get_permission_service(request: Request) -> PermissionService:
    return cast(PermissionService, request.app.state.permission_service)


__all__ = [
    "DefaultPermissionService",
    "PermissionDenied",
    "PermissionService",
    "get_permission_service",
]
