# ruff: noqa

"""权限计算、角色继承、临时授权与字段裁剪。

该模块保持纯 Python 的确定性计算；持久化入口由 API/迁移层提供，方便离线
权限检查、MCP 和网页路由共用完全相同的规则。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from crosserp.api.errors import APIError, ErrorCode

if TYPE_CHECKING:
    from crosserp.platform.principal import Principal

Effect = Literal["allow", "deny"]


@dataclass(frozen=True)
class PermissionDecision:
    permission: str
    allowed: bool
    sources: tuple[str, ...] = ()
    denied_by: tuple[str, ...] = ()
    data_scopes: tuple[str, ...] = ()


@dataclass
class RoleRecord:
    id: str
    name: str | None = None
    parent_ids: set[str] = field(default_factory=set)
    permissions: dict[str, Effect] = field(default_factory=dict)
    data_scopes: set[str] = field(default_factory=set)
    active: bool = True


@dataclass
class GrantRecord:
    user_id: UUID
    permission: str
    effect: Effect
    reason: str
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    temporary: bool = False


LEGACY_PERMISSION_MAP: dict[str, str] = {
    "report.read": "report:read",
    "issue.handle": "issue:write",
    "import.run": "integration:import",
    "voucher.draft": "journal_entry:create",
    "approval.submit": "approval:create",
    "approval.decide": "approval:approve",
    "voucher.download": "journal_entry:export",
    "ai.ask": "agent_tool:read",
    "audit.read": "audit_log:read",
    "audit.export": "audit_log:export",
    "security_log.read": "audit_log:read",
    "llm_monitor.read": "agent_tool:read",
    "user.manage": "user_admin:write",
    "setting.manage": "system:write",
    "budget.manage": "budget:write",
}

TEMPLATE_ROLE_IDS = (
    "owner_manager",
    "store_operator",
    "operations_manager",
    "advertising",
    "product_developer",
    "purchaser",
    "warehouse_logistics",
    "customer_service",
    "accountant",
    "finance_manager",
    "cashier",
    "hr_admin",
    "employee",
    "department_manager",
    "auditor_template",
    "external_viewer",
)


class IAMService:
    """线程内可复用的权限服务实现。

    角色和授权记录由 API 启动时从数据库装载；未装载时仍支持 Principal
    自带 roles/permissions，保证旧入口和演示环境兼容。
    """

    def __init__(self) -> None:
        self.roles: dict[str, RoleRecord] = {}
        self.user_roles: dict[UUID, set[str]] = {}
        self.overrides: dict[UUID, list[GrantRecord]] = {}
        self.temporary_grants: dict[UUID, list[GrantRecord]] = {}
        self._versions: dict[UUID, int] = {}
        self.seed_templates()

    def seed_templates(self) -> None:
        """装载前端定义的 16 个模板，演示默认值需在正式使用前核实。"""
        from crosserp.iam.catalog import load_role_templates

        template_permissions = load_role_templates()
        for role_id in TEMPLATE_ROLE_IDS:
            if role_id in self.roles:
                continue
            self.create_role(
                role_id,
                name=role_id,
                permissions=set(template_permissions.get(role_id, ())),
                data_scopes={"all"},
            )
        self.roles["operations_manager"].parent_ids = {"store_operator"}
        self.roles["finance_manager"].parent_ids = {"accountant"}
        self.roles["department_manager"].parent_ids = {"employee"}

    def create_role(
        self,
        role_id: str,
        *,
        name: str | None = None,
        permissions: set[str] | None = None,
        parent_ids: set[str] | None = None,
        data_scopes: set[str] | None = None,
    ) -> RoleRecord:
        if role_id in self.roles:
            raise ValueError(f"角色已存在: {role_id}")
        role = RoleRecord(
            role_id,
            name=name,
            permissions={key: "allow" for key in permissions or set()},
            parent_ids=set(parent_ids or set()),
            data_scopes=set(data_scopes or set()),
        )
        self.roles[role_id] = role
        self._assert_no_cycle(role_id)
        return role

    def update_role(
        self,
        role_id: str,
        *,
        parent_ids: set[str] | None = None,
        permissions: dict[str, Effect] | None = None,
        active: bool | None = None,
    ) -> RoleRecord:
        role = self.roles.get(role_id)
        if role is None:
            raise KeyError(role_id)
        old = (set(role.parent_ids), dict(role.permissions), role.active)
        if parent_ids is not None:
            role.parent_ids = set(parent_ids)
        if permissions is not None:
            role.permissions = dict(permissions)
        if active is not None:
            role.active = active
        try:
            self._assert_no_cycle(role_id)
        except Exception:
            role.parent_ids, role.permissions, role.active = old
            raise
        self._bump_for_role(role_id)
        return role

    def assign_role(self, user_id: UUID, role_id: str) -> None:
        if role_id not in self.roles:
            raise KeyError(role_id)
        self.user_roles.setdefault(user_id, set()).add(role_id)
        self._bump(user_id)

    def set_override(
        self,
        user_id: UUID,
        permission: str,
        *,
        effect: Effect,
        reason: str,
        data_scopes: set[str] | None = None,
    ) -> GrantRecord:
        grant = GrantRecord(user_id, permission, effect, reason)
        self.overrides.setdefault(user_id, []).append(grant)
        self._bump(user_id)
        return grant

    def set_temporary_grant(
        self,
        user_id: UUID,
        permission: str,
        *,
        effect: Effect = "allow",
        reason: str = "temporary grant",
        starts_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> GrantRecord:
        grant = GrantRecord(
            user_id,
            permission,
            effect,
            reason,
            starts_at=starts_at,
            expires_at=expires_at,
            temporary=True,
        )
        self.temporary_grants.setdefault(user_id, []).append(grant)
        self._bump(user_id)
        return grant

    def permission_version(self, user_id: UUID) -> int:
        return self._versions.get(user_id, 0)

    def effective_permission(
        self,
        user_id: UUID,
        permission: str,
        *,
        principal: Principal | None = None,
        now: datetime | None = None,
    ) -> PermissionDecision:
        now = now or datetime.now(UTC)
        allows: list[str] = []
        denies: list[str] = []
        scopes: set[str] = set()
        roles = set(self.user_roles.get(user_id, set()))
        if principal is not None:
            roles.update(principal.roles)
        visited: set[str] = set()
        for role_id in roles:
            for inherited in self._role_chain(role_id, visited):
                role = self.roles.get(inherited)
                if role is None or not role.active:
                    continue
                effect = role.permissions.get(permission)
                if effect == "deny":
                    denies.append(f"角色 {inherited}")
                elif effect == "allow":
                    allows.append(f"角色 {inherited}")
                    scopes.update(role.data_scopes)
        if principal is not None and permission in principal.permissions:
            allows.append("Principal")
        for grant in [*self.overrides.get(user_id, []), *self.temporary_grants.get(user_id, [])]:
            if grant.permission != permission or not _active(grant, now):
                continue
            source = f"{'临时授权' if grant.temporary else '用户例外'}：{grant.reason}"
            (denies if grant.effect == "deny" else allows).append(source)
        return PermissionDecision(
            permission,
            bool(allows) and not denies,
            tuple(allows),
            tuple(denies),
            tuple(sorted(scopes)),
        )

    def require(
        self,
        principal: Principal,
        permission: str,
        resource: Any = None,
        *,
        allowed_permissions: set[str] | None = None,
        risk_tier: str | None = None,
    ) -> None:
        requested = permission
        if requested in LEGACY_PERMISSION_MAP:
            requested = LEGACY_PERMISSION_MAP[requested]
        if principal.is_agent:
            if allowed_permissions is not None and requested not in allowed_permissions:
                raise PermissionError(requested)
            if risk_tier == "critical" or _looks_critical(requested):
                raise PermissionError(requested)
        decision = self.effective_permission(
            principal.effective_user_id or principal.user_id or UUID(int=0),
            requested,
            principal=principal,
        )
        if not decision.allowed and requested != permission:
            decision = self.effective_permission(
                principal.effective_user_id or principal.user_id or UUID(int=0),
                permission,
                principal=principal,
            )
        if not decision.allowed and permission not in {"public", "authenticated"}:
            raise APIError(
                ErrorCode.FORBIDDEN,
                "无权执行该操作",
                details={"permission": permission},
            )

    def data_scope_filter(self, principal: Principal, entity: str) -> dict[str, Any]:
        decision = self.effective_permission(
            principal.effective_user_id or principal.user_id or UUID(int=0),
            entity,
            principal=principal,
        )
        scopes = set(decision.data_scopes)
        if isinstance(principal.data_scope, dict):
            allowed = set(principal.data_scope.get("scopes", principal.data_scope.keys()))
            scopes &= allowed
        elif principal.data_scope:
            scopes &= {str(principal.data_scope)}
        return {"entity": entity, "scopes": sorted(scopes)}

    def serialize(
        self, user_id: UUID, record: dict[str, Any], field_permissions: dict[str, str]
    ) -> dict[str, Any]:
        return {
            key: value
            for key, value in record.items()
            if key not in field_permissions
            or self.effective_permission(user_id, field_permissions[key]).allowed
        }

    def _role_chain(self, role_id: str, visited: set[str]) -> set[str]:
        if role_id in visited:
            return set()
        visited.add(role_id)
        role = self.roles.get(role_id)
        if role is None:
            return {role_id}
        result = {role_id}
        for parent in role.parent_ids:
            result.update(self._role_chain(parent, visited))
        return result

    def _assert_no_cycle(self, role_id: str) -> None:
        def walk(current: str, path: set[str]) -> None:
            if current in path:
                raise ValueError("角色继承存在循环")
            role = self.roles.get(current)
            if role is None:
                raise ValueError(f"父角色不存在: {current}")
            for parent in role.parent_ids:
                walk(parent, path | {current})

        walk(role_id, set())

    def _bump(self, user_id: UUID) -> None:
        self._versions[user_id] = self.permission_version(user_id) + 1

    def _bump_for_role(self, role_id: str) -> None:
        for user_id, roles in self.user_roles.items():
            if role_id in roles:
                self._bump(user_id)


def _active(grant: GrantRecord, now: datetime) -> bool:
    return not (grant.starts_at and grant.starts_at > now) and not (
        grant.expires_at and grant.expires_at <= now
    )


def _looks_critical(permission: str) -> bool:
    action = permission.rsplit(":", 1)[-1]
    return action in {"write", "create", "update", "delete", "approve", "export"}


__all__ = ["IAMService", "LEGACY_PERMISSION_MAP", "PermissionDecision"]
