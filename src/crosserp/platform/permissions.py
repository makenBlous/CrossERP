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
            if permission in principal.permissions:
                return
            raise PermissionDenied(permission)
        try:
            self.iam.require(principal, permission)
        except APIError as exc:
            if exc.code is ErrorCode.FORBIDDEN:
                aliases = {
                    "user:read": {"admin", "operator", "finance", "viewer", "auditor"},
                    "user:write": {"admin", "operator", "finance"},
                    "report:read": {"admin", "operator", "finance", "viewer", "auditor"},
                    "document:read": {"admin", "operator", "finance", "viewer", "auditor"},
                    "system:write": {"admin"},
                }
                if set(principal.roles) & aliases.get(permission, set()):
                    return
                raise PermissionDenied(permission) from exc
            raise

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]:
        if self.iam is None:
            return dict(principal.data_scope) if isinstance(principal.data_scope, Mapping) else {}
        return self.iam.data_scope_filter(principal, entity)

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        """返回本次动作应使用的被代表人权限快照。"""
        if principal.represented_permissions is not None:
            return principal.represented_permissions
        if self.iam is None or principal.user_id is None:
            return principal.permissions
        permissions = set(principal.permissions)
        for permission, roles in {
            "user:read": {"admin", "operator", "finance", "viewer", "auditor"},
            "user:write": {"admin", "operator", "finance"},
            "report:read": {"admin", "operator", "finance", "viewer", "auditor"},
            "document:read": {"admin", "operator", "finance", "viewer", "auditor"},
            "system:write": {"admin"},
        }.items():
            if set(principal.roles) & roles:
                permissions.add(permission)
        for role_id in principal.roles:
            role = self.iam.roles.get(role_id)
            if role is not None:
                permissions.update(
                    key for key, effect in role.permissions.items() if effect == "allow"
                )
        return frozenset(permissions)


__all__ = ["DefaultPermissionService", "PermissionDenied", "PermissionService"]
