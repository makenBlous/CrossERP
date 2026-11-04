"""用户与角色的数据库读写。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.passwords import hash_password
from crosserp.auth.roles import Role
from crosserp.db.schema import AppUser, UserRole


def create_user(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    roles: list[Role] | tuple[Role, ...] = (),
    granted_by: UUID | None = None,
    must_change_password: bool = False,
) -> AppUser:
    """创建用户并授予初始角色。调用方负责事务和审计。"""
    username = username.strip()
    if not username or len(username) > 64:
        raise ValueError("用户名不能为空且不能超过 64 个字符")
    if len(password) < 10:
        raise ValueError("密码至少 10 个字符")
    now = datetime.now(UTC)
    user = AppUser(
        id=uuid4(),
        username=username,
        display_name=(display_name or username).strip(),
        password_hash=hash_password(password),
        is_active=True,
        failed_logins=0,
        locked_until=None,
        password_changed_at=now,
        must_change_password=must_change_password,
        created_at=now,
    )
    session.add(user)
    session.flush()
    for role in roles:
        grant_role(session, user.id, role, granted_by=granted_by)
    return user


def get_by_username(session: Session, username: str) -> AppUser | None:
    return session.scalar(select(AppUser).where(AppUser.username == username.strip()))


def grant_role(
    session: Session, user_id: UUID, role: Role | str, *, granted_by: UUID | None = None
) -> UserRole:
    role_value = _role_value(role)
    existing = session.get(UserRole, (user_id, role_value))
    if existing is not None:
        return existing
    row = UserRole(
        user_id=user_id,
        role=role_value,
        granted_by=granted_by,
        granted_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row


def revoke_role(session: Session, user_id: UUID, role: Role | str) -> bool:
    row = session.get(UserRole, (user_id, _role_value(role)))
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True


def set_active(session: Session, user_id: UUID, active: bool) -> AppUser:
    user = _get_user(session, user_id)
    user.is_active = active
    session.flush()
    return user


def set_password(
    session: Session, user_id: UUID, password: str, *, must_change_password: bool = False
) -> AppUser:
    if len(password) < 10:
        raise ValueError("密码至少 10 个字符")
    user = _get_user(session, user_id)
    user.password_hash = hash_password(password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = must_change_password
    user.failed_logins = 0
    user.locked_until = None
    session.flush()
    return user


def list_users(session: Session) -> list[tuple[AppUser, tuple[str, ...]]]:
    users = list(session.scalars(select(AppUser).order_by(AppUser.username)))
    roles: dict[UUID, list[str]] = {}
    for row in session.scalars(select(UserRole).order_by(UserRole.role)):
        roles.setdefault(row.user_id, []).append(row.role)
    return [(user, tuple(roles.get(user.id, ()))) for user in users]


def _get_user(session: Session, user_id: UUID) -> AppUser:
    user = session.get(AppUser, user_id)
    if user is None:
        raise LookupError(f"用户不存在: {user_id}")
    return user


def _role_value(role: Role | str) -> str:
    value = role.value if isinstance(role, Role) else role
    try:
        return Role(value).value
    except ValueError as exc:
        raise ValueError(f"不认识的角色: {value}") from exc
