# ruff: noqa

"""跨入口权限服务协议与旧权限矩阵桥接实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from crosserp.api.errors import APIError, ErrorCode
from crosserp.iam.service import IAMService, LEGACY_PERMISSION_MAP
from crosserp.platform.principal import Principal


class PermissionDenied(APIError):
    def __init__(self, permission: str) -> None:
        super().__init__(ErrorCode.FORBIDDEN, "无权执行该操作", details={"permission": permission})


class PermissionService(Protocol):
    def require(self, principal: Principal, permission: str, resource: Any = None) -> None: ...

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]: ...


class DefaultPermissionService:
    """IAM 权限服务适配器，同时保留旧 15 点兼容检查。"""

    def __init__(self, iam: IAMService | None = None) -> None:
        self.iam = iam or IAMService()
        self._seed_legacy_roles()

    def _seed_legacy_roles(self) -> None:
        from crosserp.iam.catalog import load_catalog

        all_points = {str(point["key"]) for point in load_catalog()}
        role_points = {
            "admin": all_points | set(LEGACY_PERMISSION_MAP.values()),
            "operator": {"report:read", "integration:import", "agent_tool:read"},
            "finance": {"report:read", "approval:approve", "journal_entry:export"},
            "viewer": {"report:read", "agent_tool:read"},
            "auditor": {"report:read", "audit_log:read", "audit_log:export"},
        }
        for role, points in role_points.items():
            if role not in self.iam.roles:
                self.iam.create_role(role, permissions=points, data_scopes={"all"})

    def require(self, principal: Principal, permission: str, resource: Any = None) -> None:
        if permission in {"public", "authenticated"}:
            if permission == "authenticated" and principal.user_id is None:
                raise PermissionDenied(permission)
            return
        try:
            self.iam.require(principal, permission, resource)
            return
        except (APIError, PermissionError) as exc:
            raise PermissionDenied(permission) from exc

    def data_scope_filter(self, principal: Principal, entity: str) -> Mapping[str, Any]:
        result = self.iam.data_scope_filter(principal, entity)
        if result.get("scopes"):
            return result
        if principal.data_scope is None:
            return result
        if isinstance(principal.data_scope, Mapping):
            return dict(principal.data_scope)
        return {"scope": principal.data_scope}


__all__ = ["DefaultPermissionService", "PermissionDenied", "PermissionService"]
