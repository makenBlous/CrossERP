# ruff: noqa

"""基于数据库的确定性权限计算服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from crosserp.db.schema import (
    AppUser,
    IamDataScopeRule,
    IamFieldPolicy,
    IamPermissionOverride,
    IamRole,
    IamRoleInheritance,
    IamRolePermission,
    IamTemporaryGrant,
    UserRole,
)

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


@dataclass(frozen=True)
class RoleRecord:
    id: str
    name: str
    parent_ids: set[str]
    permissions: dict[str, Effect]
    data_scopes: set[str]
    active: bool = True


@dataclass(frozen=True)
class GrantRecord:
    user_id: UUID
    permission: str
    effect: Effect
    reason: str
    starts_at: datetime
    expires_at: datetime | None = None
    temporary: bool = False


# 08 v4 规定的旧 15 点入口映射，供统一权限服务解析现有网页动作。
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


class IAMService:
    """从数据库读取角色、授权和权限策略，并提供统一计算入口。"""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.roles: dict[str, RoleRecord] = {}
        self.user_roles: dict[UUID, set[str]] = {}
        self._refresh_roles()

    def create_role(
        self,
        role_id: str,
        *,
        name: str,
        permissions: set[str],
        parent_ids: set[str],
        data_scopes: set[str],
    ) -> RoleRecord:
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            if session.scalar(select(IamRole).where(IamRole.slug == role_id)) is not None:
                raise _api_error("VALIDATION_FAILED", f"角色已存在: {role_id}")
            parent_rows = {
                parent: session.scalar(select(IamRole).where(IamRole.slug == parent))
                for parent in parent_ids
            }
            if any(row is None for row in parent_rows.values()):
                missing = next(parent for parent, row in parent_rows.items() if row is None)
                raise _api_error("VALIDATION_FAILED", f"父角色不存在: {missing}")
            resolved_parents = {
                parent: row for parent, row in parent_rows.items() if row is not None
            }
            row = IamRole(
                slug=role_id,
                name=name,
                parent_ids=sorted(parent_ids),
                permissions={key: "allow" for key in permissions},
                data_scopes=sorted(data_scopes),
                is_active=True,
                is_template=False,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            session.add_all(
                IamRolePermission(role_id=row.id, permission=permission, effect="allow")
                for permission in permissions
            )
            session.add_all(
                IamRoleInheritance(role_id=row.id, parent_role_id=resolved_parents[parent].id)
                for parent in parent_ids
            )
        self._refresh_roles()
        return self.roles[role_id]

    def update_role(
        self,
        role_id: str,
        *,
        parent_ids: set[str] | None = None,
        permissions: dict[str, Effect] | None = None,
        active: bool | None = None,
    ) -> RoleRecord:
        self._refresh_roles()
        current = self.roles.get(role_id)
        if current is None:
            raise _api_error("NOT_FOUND", f"角色不存在: {role_id}")
        candidate = RoleRecord(
            role_id,
            current.name,
            set(current.parent_ids if parent_ids is None else parent_ids),
            dict(current.permissions if permissions is None else permissions),
            set(current.data_scopes),
            current.active if active is None else active,
        )
        candidates = dict(self.roles)
        candidates[role_id] = candidate
        self._assert_no_cycle(role_id, candidates)
        self._persist_role(candidate)
        self._refresh_roles()
        return self.roles[role_id]

    def assign_role(self, user_id: UUID, role_id: str) -> None:
        with Session(self.engine) as session, session.begin():
            if session.scalar(select(IamRole).where(IamRole.slug == role_id)) is None:
                raise _api_error("NOT_FOUND", f"角色不存在: {role_id}")
            user = session.get(AppUser, user_id)
            if user is None:
                raise _api_error("NOT_FOUND", f"用户不存在: {user_id}")
            if session.get(UserRole, {"user_id": user_id, "role": role_id}) is None:
                session.add(UserRole(user_id=user_id, role=role_id, granted_at=datetime.now(UTC)))
                user.permission_version += 1
        self._refresh_roles()

    def set_override(
        self,
        user_id: UUID,
        permission: str,
        *,
        effect: Effect,
        reason: str,
        data_scopes: set[str] | None = None,
    ) -> GrantRecord:
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            user = session.get(AppUser, user_id)
            if user is None:
                raise _api_error("NOT_FOUND", f"用户不存在: {user_id}")
            session.add(
                IamPermissionOverride(
                    user_id=user_id,
                    permission=permission,
                    effect=effect,
                    reason=reason,
                    data_scopes=[] if data_scopes is None else sorted(data_scopes),
                    starts_at=None,
                    expires_at=None,
                    created_at=now,
                )
            )
            user.permission_version += 1
        self._refresh_roles()
        return GrantRecord(user_id, permission, effect, reason, now)

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
        now = datetime.now(UTC)
        starts = starts_at or now
        expires = expires_at or starts + timedelta(hours=1)
        with Session(self.engine) as session, session.begin():
            user = session.get(AppUser, user_id)
            if user is None:
                raise _api_error("NOT_FOUND", f"用户不存在: {user_id}")
            session.add(
                IamTemporaryGrant(
                    user_id=user_id,
                    permission=permission,
                    effect=effect,
                    reason=reason,
                    starts_at=starts,
                    expires_at=expires,
                    created_at=now,
                )
            )
            user.permission_version += 1
        self._refresh_roles()
        return GrantRecord(user_id, permission, effect, reason, starts, expires, True)

    def permission_version(self, user_id: UUID) -> int:
        with Session(self.engine) as session:
            user = session.get(AppUser, user_id)
            if user is None:
                raise _api_error("NOT_FOUND", f"用户不存在: {user_id}")
            return int(user.permission_version)

    def effective_permission(
        self,
        user_id: UUID,
        permission: str,
        *,
        principal: Principal | None = None,
        now: datetime | None = None,
    ) -> PermissionDecision:
        checked_at = datetime.now(UTC) if now is None else now
        self._refresh_roles()
        with Session(self.engine) as session:
            roles = set(session.scalars(select(UserRole.role).where(UserRole.user_id == user_id)))
            overrides = [
                GrantRecord(
                    row.user_id,
                    row.permission,
                    cast(Effect, row.effect),
                    row.reason,
                    row.starts_at or checked_at,
                    row.expires_at,
                )
                for row in session.scalars(
                    select(IamPermissionOverride).where(IamPermissionOverride.user_id == user_id)
                )
            ]
            temporary = [
                GrantRecord(
                    row.user_id,
                    row.permission,
                    cast(Effect, row.effect),
                    row.reason,
                    row.starts_at,
                    row.expires_at,
                    True,
                )
                for row in session.scalars(
                    select(IamTemporaryGrant).where(IamTemporaryGrant.user_id == user_id)
                )
                if row.revoked_at is None
            ]
        if principal is not None:
            roles.update(principal.roles)
        allows: list[str] = []
        denies: list[str] = []
        scopes: set[str] = set()
        visited: set[str] = set()
        for role_id in roles:
            for inherited in self._role_chain(role_id, visited):
                role = self.roles[inherited]
                if not role.active:
                    continue
                effect = role.permissions.get(permission)
                if effect == "deny":
                    denies.append(f"角色 {inherited}")
                elif effect == "allow":
                    allows.append(f"角色 {inherited}")
                    scopes.update(role.data_scopes)
        if principal is not None and permission in principal.permissions:
            allows.append("Principal")
        for grant in [*overrides, *temporary]:
            if grant.permission != permission or not _active(grant, checked_at):
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
        *,
        allowed_permissions: set[str] | None = None,
        risk_tier: str | None = None,
    ) -> None:
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            raise _api_error("AUTH_REQUIRED", "需要登录")
        requested = LEGACY_PERMISSION_MAP.get(permission, permission)
        if principal.is_agent:
            if allowed_permissions is not None and requested not in allowed_permissions:
                raise _api_error("AI_AUTONOMY_CAPPED", "智能体超出委托权限")
            if risk_tier == "critical":
                raise _api_error("AI_AUTONOMY_CAPPED", "智能体不能执行危风险动作")
        decision = self.effective_permission(
            effective_user_id,
            requested,
            principal=principal,
        )
        if not decision.allowed and permission not in {"public", "authenticated"}:
            raise _api_error("FORBIDDEN", "无权执行该操作", {"permission": permission})

    def data_scope_filter(self, principal: Principal, entity: str) -> dict[str, Any]:
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            raise _api_error("AUTH_REQUIRED", "需要登录")
        decision = self.effective_permission(effective_user_id, entity, principal=principal)
        scopes = set(decision.data_scopes)
        if isinstance(principal.data_scope, dict):
            allowed = set(principal.data_scope.get("scopes", principal.data_scope.keys()))
            scopes &= allowed
        elif principal.data_scope:
            scopes &= {str(principal.data_scope)}
        with Session(self.engine) as session:
            rules = list(
                session.scalars(
                    select(IamDataScopeRule).where(IamDataScopeRule.entity.in_((entity, "*")))
                )
            )
        filters = {row.scope_type: row.values for row in rules}
        return {"entity": entity, "scopes": sorted(scopes | set(filters)), "filters": filters}

    def serialize(
        self, user_id: UUID, record: dict[str, Any], field_permissions: dict[str, str]
    ) -> dict[str, Any]:
        with Session(self.engine) as session:
            policies = list(session.scalars(select(IamFieldPolicy)))
        policy_permissions = {row.field_key: row.permission for row in policies}
        policy_permissions.update(field_permissions)
        return {
            key: value
            for key, value in record.items()
            if key not in policy_permissions
            or self.effective_permission(user_id, policy_permissions[key]).allowed
        }

    def _role_chain(self, role_id: str, visited: set[str]) -> set[str]:
        if role_id in visited:
            return set()
        role = self.roles.get(role_id)
        if role is None:
            raise _api_error("NOT_FOUND", f"角色不存在: {role_id}")
        visited.add(role_id)
        result = {role_id}
        for parent in role.parent_ids:
            result.update(self._role_chain(parent, visited))
        return result

    @staticmethod
    def _assert_no_cycle(role_id: str, roles: dict[str, RoleRecord]) -> None:
        def walk(current: str, path: set[str]) -> None:
            if current in path:
                raise _api_error("VALIDATION_FAILED", "角色继承存在循环")
            role = roles.get(current)
            if role is None:
                raise _api_error("VALIDATION_FAILED", f"父角色不存在: {current}")
            for parent in role.parent_ids:
                walk(parent, path | {current})

        walk(role_id, set())

    def _refresh_roles(self) -> None:
        with Session(self.engine) as session:
            self.roles = {
                row.slug: RoleRecord(
                    row.slug,
                    row.name,
                    set(row.parent_ids),
                    {key: cast(Effect, value) for key, value in row.permissions.items()},
                    set(row.data_scopes),
                    row.is_active,
                )
                for row in session.scalars(select(IamRole))
            }
            self.user_roles = {}
            for user_id, role in session.execute(select(UserRole.user_id, UserRole.role)):
                self.user_roles.setdefault(user_id, set()).add(role)

    def _persist_role(self, role: RoleRecord) -> None:
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            row = session.scalar(select(IamRole).where(IamRole.slug == role.id))
            if row is None:
                raise _api_error("NOT_FOUND", f"角色不存在: {role.id}")
            parent_rows = {
                parent: session.scalar(select(IamRole).where(IamRole.slug == parent))
                for parent in role.parent_ids
            }
            if any(parent is None for parent in parent_rows.values()):
                missing = next(parent for parent, value in parent_rows.items() if value is None)
                raise _api_error("VALIDATION_FAILED", f"父角色不存在: {missing}")
            resolved_parents = {
                parent: value for parent, value in parent_rows.items() if value is not None
            }
            row.parent_ids = sorted(role.parent_ids)
            row.permissions = dict(role.permissions)
            row.data_scopes = sorted(role.data_scopes)
            row.is_active = role.active
            row.updated_at = now
            session.execute(delete(IamRoleInheritance).where(IamRoleInheritance.role_id == row.id))
            session.execute(delete(IamRolePermission).where(IamRolePermission.role_id == row.id))
            session.add_all(
                IamRoleInheritance(role_id=row.id, parent_role_id=resolved_parents[parent].id)
                for parent in role.parent_ids
            )
            session.add_all(
                IamRolePermission(role_id=row.id, permission=permission, effect=effect)
                for permission, effect in role.permissions.items()
            )
            user_ids = select(UserRole.user_id).where(UserRole.role == role.id)
            session.execute(
                update(AppUser)
                .where(AppUser.id.in_(user_ids))
                .values(permission_version=AppUser.permission_version + 1)
            )


def _active(grant: GrantRecord, now: datetime) -> bool:
    if grant.starts_at > now:
        return False
    return grant.expires_at is None or grant.expires_at > now


def _api_error(code: str, message: str, details: dict[str, Any] | None = None) -> Exception:
    from crosserp.api.errors import APIError, ErrorCode

    return APIError(ErrorCode(code), message, details=details)


__all__ = ["IAMService", "LEGACY_PERMISSION_MAP", "PermissionDecision"]
