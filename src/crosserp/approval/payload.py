"""审批对象的确定性内容哈希。"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import ProfitSnapshot, Store, Voucher
from crosserp.vouchers.service import voucher_payload


def payload_hash(session: Session, target_type: str, target_id: str) -> str:
    """计算利润报表或凭证当前内容哈希。"""
    if target_type == "voucher":
        row = session.get(Voucher, UUID(target_id))
        if row is None:
            raise LookupError(f"凭证不存在 {target_id}")
        return voucher_payload(row, session)
    if target_type == "profit_report":
        store_name, separator, period = target_id.rpartition(":")
        if not separator or not store_name or len(period) != 7:
            raise ValueError("利润报表对象必须是 店铺:YYYY-MM")
        statement = (
            select(ProfitSnapshot.inputs_hash)
            .join(Store, ProfitSnapshot.store_id == Store.id)
            .where(ProfitSnapshot.period == period, Store.name == store_name)
            .order_by(ProfitSnapshot.internal_sku)
        )
        values = [str(value) for value in session.scalars(statement)]
        if not values:
            raise LookupError(f"找不到利润报表 {target_id}")
        return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()
    raise ValueError(f"不支持的审批对象类型: {target_type}")


def compute(session: Session, target_type: str, target_id: str) -> str:
    """统一审批 payload 计算入口。"""
    return payload_hash(session, target_type, target_id)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
