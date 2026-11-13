# ruff: noqa

"""基于数据库的确定性权限计算服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from crosserp.db.schema import (
    AgentStoreScope,
    AppUser,
    IamDataScopeRule,
    IamFieldPolicy,
    IamPermissionOverride,
    IamRole,
    IamRoleInheritance,
    IamRolePermission,
    IamTemporaryGrant,
    Store,
    UserRole,
    UserStoreGrant,
)
from crosserp.iam.scope import (
    LegalEntityScope,
    PeriodScope,
    StoreScope,
    choose_entity_rules,
    resolve_legal_entity_scope,
    resolve_period_scope,
    resolve_store_scope,
    role_tokens_for_dimension,
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

    def current_permissions(self, principal: Principal) -> frozenset[str]:
        """返回数据库中当前有效的权限点，不读取 Principal 快照。"""
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            return frozenset()
        self._refresh_roles()
        with Session(self.engine) as session:
            role_ids = set(
                session.scalars(select(UserRole.role).where(UserRole.user_id == effective_user_id))
            )
            candidates: set[str] = set()
            visited: set[str] = set()
            for role_id in role_ids:
                for inherited in self._role_chain(role_id, visited):
                    candidates.update(self.roles[inherited].permissions)
            candidates.update(
                session.scalars(
                    select(IamPermissionOverride.permission).where(
                        IamPermissionOverride.user_id == effective_user_id
                    )
                )
            )
            candidates.update(
                session.scalars(
                    select(IamTemporaryGrant.permission).where(
                        IamTemporaryGrant.user_id == effective_user_id,
                        IamTemporaryGrant.revoked_at.is_(None),
                    )
                )
            )
        return frozenset(
            permission
            for permission in candidates
            if self.effective_permission(effective_user_id, permission).allowed
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
        with Session(self.engine) as session:
            role_ids = self._role_uuid_ids(session, self._active_role_slugs(effective_user_id))
            rules = self._applicable_scope_rules(session, entity, role_ids)
            filters = {row.scope_type: row.values for row in rules}
        return {"entity": entity, "scopes": sorted(scopes | set(filters)), "filters": filters}

    def store_scope(self, principal: Principal, entity: str) -> StoreScope:
        """返回全部店铺或店铺 id 集合。规则缺失或格式不对时拒绝放行。"""
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            raise _api_error("AUTH_REQUIRED", "需要登录")
        role_tokens = self._role_store_tokens(effective_user_id)
        checked_at = datetime.now(UTC)
        with Session(self.engine) as session:
            role_ids = self._role_uuid_ids(session, self._active_role_slugs(effective_user_id))
            rules = self._applicable_scope_rules(session, entity, role_ids)
            owned_store_ids = frozenset(
                session.scalars(
                    select(UserStoreGrant.store_id).where(
                        UserStoreGrant.user_id == effective_user_id
                    )
                )
            )
            allow_tokens, deny_tokens = self._scope_exception_tokens(
                session, effective_user_id, checked_at
            )
            universe_store_ids = frozenset(session.scalars(select(Store.id)))
            apply_agent_narrowing, agent_store_ids = self._agent_store_ids(session, principal)
        role_rules, global_rules = self._split_scope_rules(rules, entity)
        return resolve_store_scope(
            role_tokens,
            role_rules=role_rules,
            global_rules=global_rules,
            owned_store_ids=owned_store_ids,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
            apply_agent_narrowing=apply_agent_narrowing,
            agent_store_ids=agent_store_ids,
            universe_store_ids=universe_store_ids,
        )

    def _active_role_slugs(self, user_id: UUID) -> set[str]:
        self._refresh_roles()
        with Session(self.engine) as session:
            role_ids = set(
                session.scalars(select(UserRole.role).where(UserRole.user_id == user_id))
            )
        slugs: set[str] = set()
        visited: set[str] = set()
        for role_id in role_ids:
            for inherited in self._role_chain(role_id, visited):
                role = self.roles[inherited]
                if role.active:
                    slugs.add(inherited)
        return slugs

    def _role_uuid_ids(self, session: Session, slugs: set[str]) -> set[UUID]:
        if not slugs:
            return set()
        return set(session.scalars(select(IamRole.id).where(IamRole.slug.in_(slugs))))

    def _applicable_scope_rules(
        self, session: Session, entity: str, role_ids: set[UUID]
    ) -> list[IamDataScopeRule]:
        statement = select(IamDataScopeRule).where(IamDataScopeRule.entity.in_((entity, "*")))
        if role_ids:
            statement = statement.where(
                or_(IamDataScopeRule.role_id.is_(None), IamDataScopeRule.role_id.in_(role_ids))
            )
        else:
            statement = statement.where(IamDataScopeRule.role_id.is_(None))
        return list(session.scalars(statement))

    def _split_scope_rules(
        self, rules: list[IamDataScopeRule], entity: str
    ) -> tuple[list[tuple[str, Any]], list[tuple[str, Any]]]:
        grouped: dict[UUID, list[tuple[str, str, Any]]] = {}
        global_rows: list[tuple[str, str, Any]] = []
        for row in rules:
            item = (row.entity, row.scope_type, row.values)
            if row.role_id is None:
                global_rows.append(item)
                continue
            grouped.setdefault(row.role_id, []).append(item)
        role_rules: list[tuple[str, Any]] = []
        for rows in grouped.values():
            role_rules.extend(choose_entity_rules(rows, entity))
        return role_rules, choose_entity_rules(global_rows, entity)

    def _scope_exception_tokens(
        self, session: Session, user_id: UUID, checked_at: datetime
    ) -> tuple[set[str], set[str]]:
        allow: set[str] = set()
        deny: set[str] = set()
        rows = session.scalars(
            select(IamPermissionOverride).where(IamPermissionOverride.user_id == user_id)
        )
        for row in rows:
            if not _override_active(row.starts_at, row.expires_at, checked_at):
                continue
            values = row.data_scopes
            if not isinstance(values, list):
                raise _api_error("VALIDATION_FAILED", "用户例外 data_scopes 必须是数组")
            if not values:
                continue
            if row.effect not in {"allow", "deny"}:
                raise _api_error("VALIDATION_FAILED", f"用户例外 effect 无效: {row.effect}")
            target = allow if row.effect == "allow" else deny
            for item in values:
                if not isinstance(item, str):
                    raise _api_error("VALIDATION_FAILED", "用户例外 data_scopes 必须是字符串")
                target.add(item)
        return allow, deny

    def _agent_store_ids(
        self, session: Session, principal: Principal
    ) -> tuple[bool, frozenset[UUID]]:
        if not principal.is_agent:
            return False, frozenset()
        agent_id = principal.agent_id
        if agent_id is None:
            raise _api_error("VALIDATION_FAILED", "智能体数据范围缺少 agent_id")
        store_ids = frozenset(
            session.scalars(
                select(AgentStoreScope.store_id).where(AgentStoreScope.agent_id == agent_id)
            )
        )
        if not store_ids:
            return False, frozenset()
        return True, store_ids

    def period_scope(self, principal: Principal, entity: str) -> PeriodScope:
        """返回全部期间或 YYYY-MM 集合。格式不对时拒绝放行。"""
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            raise _api_error("AUTH_REQUIRED", "需要登录")
        role_tokens = self._role_store_tokens(effective_user_id)
        with Session(self.engine) as session:
            role_ids = self._role_uuid_ids(session, self._active_role_slugs(effective_user_id))
            rules = self._applicable_scope_rules(session, entity, role_ids)
        return resolve_period_scope(
            role_tokens_for_dimension(role_tokens, frozenset({"all"})),
            entity_rules=[(row.scope_type, row.values) for row in rules if row.entity == entity],
            wildcard_rules=[(row.scope_type, row.values) for row in rules if row.entity == "*"],
        )

    def legal_entity_scope(self, principal: Principal, entity: str) -> LegalEntityScope:
        """返回全部法人或法人名称集合。格式不对时拒绝放行。"""
        effective_user_id = principal.effective_user_id
        if effective_user_id is None:
            raise _api_error("AUTH_REQUIRED", "需要登录")
        role_tokens = self._role_store_tokens(effective_user_id)
        with Session(self.engine) as session:
            role_ids = self._role_uuid_ids(session, self._active_role_slugs(effective_user_id))
            rules = self._applicable_scope_rules(session, entity, role_ids)
        return resolve_legal_entity_scope(
            role_tokens_for_dimension(role_tokens, frozenset({"all"})),
            entity_rules=[(row.scope_type, row.values) for row in rules if row.entity == entity],
            wildcard_rules=[(row.scope_type, row.values) for row in rules if row.entity == "*"],
        )

    def _role_store_tokens(self, user_id: UUID) -> set[str]:
        self._refresh_roles()
        with Session(self.engine) as session:
            role_ids = set(
                session.scalars(select(UserRole.role).where(UserRole.user_id == user_id))
            )
        tokens: set[str] = set()
        visited: set[str] = set()
        for role_id in role_ids:
            for inherited in self._role_chain(role_id, visited):
                role = self.roles[inherited]
                if role.active:
                    tokens.update(role.data_scopes)
        return tokens

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


def _override_active(
    starts_at: datetime | None, expires_at: datetime | None, now: datetime
) -> bool:
    if starts_at is not None and starts_at > now:
        return False
    return expires_at is None or expires_at > now


def _api_error(code: str, message: str, details: dict[str, Any] | None = None) -> Exception:
    from crosserp.api.errors import APIError, ErrorCode

    return APIError(ErrorCode(code), message, details=details)


__all__ = ["IAMService", "LEGACY_PERMISSION_MAP", "PermissionDecision"]
