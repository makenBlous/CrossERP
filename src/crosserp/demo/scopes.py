"""演示账号按角色分配负责店铺。只写调用方传入的会话。"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user, get_by_username
from crosserp.db.schema import Store, UserRole, UserStoreGrant

# 索引是排序后的店铺序号。all / 未实现维度不分配店铺。
_DEMO_ACCOUNTS: tuple[tuple[str, str, int | None], ...] = (
    ("demo-owner", "owner_manager", None),
    ("demo-store-operator", "store_operator", 0),
    ("demo-advertising", "advertising", 1),
    ("demo-customer-service", "customer_service", 0),
    ("demo-ops-manager", "operations_manager", 0),
    ("demo-product", "product_developer", None),
    ("demo-purchaser", "purchaser", None),
    ("demo-warehouse", "warehouse_logistics", None),
    ("demo-accountant", "accountant", None),
    ("demo-finance", "finance_manager", None),
    ("demo-cashier", "cashier", None),
    ("demo-hr", "hr_admin", None),
    ("demo-employee", "employee", None),
    ("demo-dept", "department_manager", None),
    ("demo-auditor", "auditor_template", None),
    ("demo-viewer", "external_viewer", 1),
)


def seed_demo_role_accounts(session: Session, *, granted_by: UUID) -> list[tuple[str, str]]:
    """创建缺失的演示角色账号并把负责店铺写进 user_store_grant。"""
    stores = list(session.scalars(select(Store).order_by(Store.name, Store.id)))
    if not stores:
        raise RuntimeError("演示库没有店铺 不能分配角色数据范围")
    created: list[tuple[str, str]] = []
    now = datetime.now(UTC)
    for username, role_id, store_index in _DEMO_ACCOUNTS:
        user = get_by_username(session, username)
        password = ""
        if user is None:
            password = secrets.token_urlsafe(18)
            user = create_user(session, username=username, password=password)
            created.append((username, password))
        if session.get(UserRole, (user.id, role_id)) is None:
            session.add(
                UserRole(
                    user_id=user.id,
                    role=role_id,
                    granted_by=granted_by,
                    granted_at=now,
                )
            )
        if store_index is None:
            continue
        store = stores[store_index % len(stores)]
        existing = session.get(UserStoreGrant, (user.id, store.id))
        if existing is None:
            session.add(
                UserStoreGrant(
                    user_id=user.id,
                    store_id=store.id,
                    granted_by=granted_by,
                    granted_at=now,
                )
            )
    session.flush()
    return created
