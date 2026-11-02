"""店铺读写样例。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from crosserp.db.dialects import upsert
from crosserp.db.schema import Store


def get_store(session: Session, store_id: UUID) -> Store | None:
    """按主键读取店铺。"""
    return session.get(Store, store_id)


def upsert_store(
    session: Session,
    *,
    store_id: UUID,
    platform: str,
    marketplace: str,
    name: str,
    currency: str,
) -> None:
    """按主键插入或更新店铺。调用方负责提交。"""
    upsert(
        session,
        Store.__table__,
        {
            "id": store_id,
            "platform": platform,
            "marketplace": marketplace,
            "name": name,
            "currency": currency,
        },
        ["id"],
        ["platform", "marketplace", "name", "currency"],
    )
