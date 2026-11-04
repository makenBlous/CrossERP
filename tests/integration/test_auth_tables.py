"""W5 认证表三库通用结构测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.schema import ApiToken, AppSetting, AppUser, UserRole, UserSession

pytestmark = pytest.mark.db


def test_auth_tables_accept_unicode_and_enforce_unique_username(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        _test_auth_tables_accept_unicode_and_enforce_unique_username(engine)
    finally:
        downgrade_base(url)


def _test_auth_tables_accept_unicode_and_enforce_unique_username(engine) -> None:
    with Session(engine) as session, session.begin():
        user = create_user(
            session,
            username="财务🧾",
            display_name="财务管理员 🧾",
            password="A sufficiently long password",
            roles=(Role.ADMIN,),
        )
        session.add(
            UserSession(
                id="a" * 64,
                user_id=user.id,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
                ip="127.0.0.1",
                user_agent="测试浏览器 🧾",
                csrf_token_hash="b" * 64,
            )
        )
        session.add(
            ApiToken(
                id=uuid4(),
                user_id=user.id,
                name="测试 token",
                token_hash="c" * 64,
                scopes=["read"],
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            AppSetting(
                key="solo_mode", value_json=True, updated_by=user.id, updated_at=datetime.now(UTC)
            )
        )
    with Session(engine) as session, session.begin():
        duplicate = AppUser(
            id=uuid4(),
            username="财务🧾",
            display_name="重复",
            password_hash="x",
            is_active=True,
            failed_logins=0,
            password_changed_at=datetime.now(UTC),
            must_change_password=False,
            created_at=datetime.now(UTC),
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.flush()


def test_role_grant_is_idempotent(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        _test_role_grant_is_idempotent(engine)
    finally:
        downgrade_base(url)


def _test_role_grant_is_idempotent(engine) -> None:
    with Session(engine) as session, session.begin():
        user = create_user(
            session,
            username="operator",
            password="A sufficiently long password",
        )
        first = grant_role(session, user.id, Role.OPERATOR)
        second = grant_role(session, user.id, Role.OPERATOR)
        assert first.user_id == second.user_id
        assert (
            session.scalar(select(UserRole).where(UserRole.user_id == user.id)).role == "operator"
        )
