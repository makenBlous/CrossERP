"""网页权限依赖的通用函数。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.permissions import Permission, has_permission
from crosserp.db.schema import AppUser, UserRole


def user_roles(session: Session, user: AppUser) -> set[str]:
    return set(session.scalars(select(UserRole.role).where(UserRole.user_id == user.id)))


def require(session: Session, user: AppUser, permission: Permission | str) -> bool:
    return has_permission(user_roles(session, user), permission)
