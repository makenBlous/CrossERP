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

    def entity_in_scope(
        self,
        principal: Principal,
        entity: str,
        entity_id: str,
        resource: Mapping[str, Any] | None,
    ) -> bool: ...

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

    def entity_in_scope(
        self,
        principal: Principal,
        entity: str,
        entity_id: str,
        resource: Mapping[str, Any] | None,
    ) -> bool:
        """判断实体 ID 是否落在 data_scope_filter 给出的范围内。"""
        return entity_matches_scope(
            self.data_scope_filter(principal, entity), entity, entity_id, resource
        )

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        """返回本次动作应使用的被代表人权限快照。"""
        if self.iam is None:
            raise RuntimeError("PermissionService 必须绑定 IAMService")
        permissions = self.iam.current_permissions(principal)
        if principal.represented_permissions is not None:
            permissions &= principal.represented_permissions
        return permissions


def entity_matches_scope(
    scope: Mapping[str, Any],
    entity: str,
    entity_id: str,
    resource: Mapping[str, Any] | None,
) -> bool:
    """按 IAM 范围结构判断。resource 为 None 表示店铺范围实体行不存在。"""
    if "all" in scope["scopes"]:
        return True
    filters = scope["filters"]
    id_key = f"{entity[:1].lower()}{entity[1:]}Ids"
    allowed_ids = filters.get(id_key)
    if allowed_ids is not None and str(entity_id) not in {str(item) for item in allowed_ids}:
        return False
    allowed_stores = filters.get("storeIds")
    if allowed_stores is None:
        return True
    if resource is None:
        return False
    store_id = resource.get("storeId")
    if store_id is None:
        return True
    return str(store_id) in {str(item) for item in allowed_stores}


__all__ = [
    "DefaultPermissionService",
    "PermissionDenied",
    "PermissionService",
    "entity_matches_scope",
]
