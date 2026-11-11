# ruff: noqa

"""权限计算、角色继承、临时授权与字段裁剪。

该模块保持纯 Python 的确定性计算；持久化入口由 API/迁移层提供，方便离线
权限检查、MCP 和网页路由共用完全相同的规则。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

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

    def __init__(self, engine: Any | None = None) -> None:
        self.engine = engine
        self.roles: dict[str, RoleRecord] = {}
        self.user_roles: dict[UUID, set[str]] = {}
        self.overrides: dict[UUID, list[GrantRecord]] = {}
        self.temporary_grants: dict[UUID, list[GrantRecord]] = {}
        self._versions: dict[UUID, int] = {}
        self.seed_templates()

    def seed_templates(self) -> None:
        """装载前端定义的 16 个模板和 5 个兼容角色。

        有数据库时种子写入 ``iam_role``，内存只保留请求级快照。这样新进程
        会从同一数据库读取角色和权限，而不是重新生成一套不同的状态。
        """
        from crosserp.iam.catalog import load_role_templates

        template_permissions = load_role_templates()
        legacy = {
            "admin": set(template_permissions.get("owner_manager", ())),
            "operator": {"report:read", "integration:import", "agent_tool:read"},
            "finance": {"report:read", "approval:approve", "journal_entry:export"},
            "viewer": {"report:read", "agent_tool:read"},
            "auditor": {"report:read", "audit_log:read", "audit_log:export"},
        }
        definitions = {
            role_id: set(template_permissions.get(role_id, ())) for role_id in TEMPLATE_ROLE_IDS
        }
        definitions.update(legacy)
        parents = {
            "operations_manager": {"store_operator"},
            "finance_manager": {"accountant"},
            "department_manager": {"employee"},
        }
        if self.engine is None:
            for role_id, permissions in definitions.items():
                if role_id not in self.roles:
                    self.create_role(
                        role_id,
                        name=role_id,
                        permissions=permissions,
                        parent_ids=parents.get(role_id, set()),
                        data_scopes={"all"},
                    )
            return
        from datetime import UTC, datetime

        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from crosserp.db.schema import IamRole, IamRoleInheritance, IamRolePermission

        with Session(self.engine) as session, session.begin():
            existing = {row.slug: row for row in session.scalars(select(IamRole))}
            now = datetime.now(UTC)
            for role_id, permissions in definitions.items():
                row = existing.get(role_id)
                if row is None:
                    session.add(
                        IamRole(
                            slug=role_id,
                            name=role_id,
                            parent_ids=sorted(parents.get(role_id, set())),
                            permissions={key: "allow" for key in permissions},
                            data_scopes=["all"],
                            is_active=True,
                            is_template=role_id in TEMPLATE_ROLE_IDS,
                            created_at=now,
                            updated_at=now,
                        )
                    )
            session.flush()
            existing = {row.slug: row for row in session.scalars(select(IamRole))}
            for role_id, permissions in definitions.items():
                row = existing[role_id]
                current = {
                    item.permission
                    for item in session.scalars(
                        select(IamRolePermission).where(IamRolePermission.role_id == row.id)
                    )
                }
                for permission in permissions - current:
                    session.add(
                        IamRolePermission(role_id=row.id, permission=permission, effect="allow")
                    )
                for parent in parents.get(role_id, set()):
                    parent_row = existing[parent]
                    found = session.scalar(
                        select(IamRoleInheritance).where(
                            IamRoleInheritance.role_id == row.id,
                            IamRoleInheritance.parent_role_id == parent_row.id,
                        )
                    )
                    if found is None:
                        session.add(
                            IamRoleInheritance(role_id=row.id, parent_role_id=parent_row.id)
                        )
            session.flush()
        self._refresh_roles()

    def create_role(
        self,
        role_id: str,
        *,
        name: str | None = None,
        permissions: set[str] | None = None,
        parent_ids: set[str] | None = None,
        data_scopes: set[str] | None = None,
    ) -> RoleRecord:
        if self.engine is not None:
            from datetime import UTC, datetime

            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from crosserp.db.schema import IamRole, IamRoleInheritance, IamRolePermission

            with Session(self.engine) as session, session.begin():
                if session.scalar(select(IamRole).where(IamRole.slug == role_id)) is not None:
                    raise ValueError(f"角色已存在: {role_id}")
                now = datetime.now(UTC)
                row = IamRole(
                    slug=role_id,
                    name=name or role_id,
                    parent_ids=sorted(parent_ids or set()),
                    permissions={key: "allow" for key in permissions or set()},
                    data_scopes=sorted(data_scopes or set()),
                    is_active=True,
                    is_template=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
                for permission in permissions or set():
                    session.add(
                        IamRolePermission(role_id=row.id, permission=permission, effect="allow")
                    )
                for parent in parent_ids or set():
                    parent_row = session.scalar(select(IamRole).where(IamRole.slug == parent))
                    if parent_row is None:
                        raise ValueError(f"父角色不存在: {parent}")
                    session.add(IamRoleInheritance(role_id=row.id, parent_role_id=parent_row.id))
            self._refresh_roles()
            return self.roles[role_id]
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
        self._refresh_roles()
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
        if self.engine is not None:
            self._persist_role(role_id, role)
        return role

    def assign_role(self, user_id: UUID, role_id: str) -> None:
        if self.engine is not None:
            from datetime import UTC, datetime

            from sqlalchemy import delete, select
            from sqlalchemy.orm import Session

            from crosserp.db.schema import AppUser, UserRole

            with Session(self.engine) as session, session.begin():
                role = session.scalar(
                    select(self._role_model()).where(self._role_model().slug == role_id)
                )
                if role is None:
                    raise KeyError(role_id)
                exists = session.get(UserRole, {"user_id": user_id, "role": role_id})
                if exists is None:
                    session.add(
                        UserRole(user_id=user_id, role=role_id, granted_at=datetime.now(UTC))
                    )
                    user = session.get(AppUser, user_id)
                    if user is not None:
                        user.permission_version += 1
            self._refresh_roles()
            return
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
        if self.engine is not None:
            from datetime import UTC, datetime

            from sqlalchemy.orm import Session

            from crosserp.db.schema import AppUser, IamPermissionOverride

            with Session(self.engine) as session, session.begin():
                session.add(
                    IamPermissionOverride(
                        user_id=user_id,
                        permission=permission,
                        effect=effect,
                        reason=reason,
                        data_scopes=sorted(data_scopes or set()),
                        starts_at=None,
                        expires_at=None,
                        created_at=datetime.now(UTC),
                    )
                )
                user = session.get(AppUser, user_id)
                if user is not None:
                    user.permission_version += 1
            self._refresh_roles()
            return grant
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
        if self.engine is not None:
            from datetime import UTC, datetime

            from sqlalchemy.orm import Session

            from crosserp.db.schema import AppUser, IamTemporaryGrant

            with Session(self.engine) as session, session.begin():
                session.add(
                    IamTemporaryGrant(
                        user_id=user_id,
                        permission=permission,
                        effect=effect,
                        reason=reason,
                        starts_at=starts_at or datetime.now(UTC),
                        expires_at=expires_at or datetime.now(UTC),
                        created_at=datetime.now(UTC),
                    )
                )
                user = session.get(AppUser, user_id)
                if user is not None:
                    user.permission_version += 1
            self._refresh_roles()
            return grant
        self.temporary_grants.setdefault(user_id, []).append(grant)
        self._bump(user_id)
        return grant

    def permission_version(self, user_id: UUID) -> int:
        if self.engine is not None:
            from sqlalchemy.orm import Session

            from crosserp.db.schema import AppUser

            with Session(self.engine) as session:
                user = session.get(AppUser, user_id)
                return int(user.permission_version) if user is not None else 0
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
        self._refresh_roles()
        allows: list[str] = []
        denies: list[str] = []
        scopes: set[str] = set()
        roles = set(self.user_roles.get(user_id, set()))
        if self.engine is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from crosserp.db.schema import IamPermissionOverride, IamTemporaryGrant, UserRole

            with Session(self.engine) as session:
                roles = set(
                    session.scalars(select(UserRole.role).where(UserRole.user_id == user_id))
                )
                self.user_roles[user_id] = roles
                db_overrides = list(
                    session.scalars(
                        select(IamPermissionOverride).where(
                            IamPermissionOverride.user_id == user_id
                        )
                    )
                )
                db_temp = list(
                    session.scalars(
                        select(IamTemporaryGrant).where(IamTemporaryGrant.user_id == user_id)
                    )
                )
            overrides = [
                GrantRecord(
                    x.user_id,
                    x.permission,
                    cast(Effect, x.effect),
                    x.reason,
                    x.starts_at,
                    x.expires_at,
                )
                for x in db_overrides
            ]
            temporary = [
                GrantRecord(
                    x.user_id,
                    x.permission,
                    cast(Effect, x.effect),
                    x.reason,
                    x.starts_at,
                    x.expires_at,
                    True,
                )
                for x in db_temp
                if x.revoked_at is None
            ]
        else:
            overrides = self.overrides.get(user_id, [])
            temporary = self.temporary_grants.get(user_id, [])
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
        for grant in [*overrides, *temporary]:
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
        from crosserp.api.errors import APIError, ErrorCode

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
        result: dict[str, Any] = {"entity": entity, "scopes": sorted(scopes)}
        if self.engine is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from crosserp.db.schema import IamDataScopeRule

            with Session(self.engine) as session:
                rules = list(
                    session.scalars(
                        select(IamDataScopeRule).where(IamDataScopeRule.entity.in_((entity, "*")))
                    )
                )
            filters = {row.scope_type: row.values for row in rules}
            result["filters"] = filters
            result["scopes"] = sorted(set(result["scopes"]) | set(filters))
        return result

    def serialize(
        self, user_id: UUID, record: dict[str, Any], field_permissions: dict[str, str]
    ) -> dict[str, Any]:
        if self.engine is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from crosserp.db.schema import IamFieldPolicy

            with Session(self.engine) as session:
                policies = list(session.scalars(select(IamFieldPolicy)))
            field_permissions = {
                row.field_key: row.permission
                for row in policies
                if row.field_key not in field_permissions
            } | field_permissions
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

    def _role_model(self) -> Any:
        from crosserp.db.schema import IamRole

        return IamRole

    def _refresh_roles(self) -> None:
        if self.engine is None:
            return
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from crosserp.db.schema import IamRole, UserRole

        with Session(self.engine) as session:
            self.roles = {
                row.slug: RoleRecord(
                    row.slug,
                    name=row.name,
                    parent_ids=set(row.parent_ids or []),
                    permissions=dict(row.permissions or {}),
                    data_scopes=set(row.data_scopes or []),
                    active=bool(row.is_active),
                )
                for row in session.scalars(select(IamRole))
            }
            self.user_roles = {}
            for user_id, role in session.execute(select(UserRole.user_id, UserRole.role)):
                self.user_roles.setdefault(user_id, set()).add(role)

    def _persist_role(self, role_id: str, role: RoleRecord) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from crosserp.db.schema import (
            AppUser,
            IamRole,
            IamRoleInheritance,
            IamRolePermission,
            UserRole,
        )

        with Session(self.engine) as session, session.begin():
            row = session.scalar(select(IamRole).where(IamRole.slug == role_id))
            if row is None:
                raise KeyError(role_id)
            row.parent_ids = sorted(role.parent_ids)
            row.permissions = dict(role.permissions)
            row.data_scopes = sorted(role.data_scopes)
            row.is_active = role.active
            row.updated_at = datetime.now(UTC)
            for child in list(
                session.scalars(
                    select(IamRoleInheritance).where(IamRoleInheritance.role_id == row.id)
                )
            ):
                session.delete(child)
            for permission in list(
                session.scalars(
                    select(IamRolePermission).where(IamRolePermission.role_id == row.id)
                )
            ):
                session.delete(permission)
            session.flush()
            for parent in role.parent_ids:
                parent_row = session.scalar(select(IamRole).where(IamRole.slug == parent))
                if parent_row is None:
                    raise ValueError(f"父角色不存在: {parent}")
                session.add(IamRoleInheritance(role_id=row.id, parent_role_id=parent_row.id))
            for permission_key, effect in role.permissions.items():
                session.add(
                    IamRolePermission(role_id=row.id, permission=permission_key, effect=effect)
                )
            for user_id in session.scalars(
                select(UserRole.user_id).where(UserRole.role == role_id)
            ):
                user = session.get(AppUser, user_id)
                if user is not None:
                    user.permission_version += 1


def _active(grant: GrantRecord, now: datetime) -> bool:
    return not (grant.starts_at and grant.starts_at > now) and not (
        grant.expires_at and grant.expires_at <= now
    )


def _looks_critical(permission: str) -> bool:
    action = permission.rsplit(":", 1)[-1]
    return action in {"write", "create", "update", "delete", "approve", "export"}


__all__ = ["IAMService", "LEGACY_PERMISSION_MAP", "PermissionDecision"]
