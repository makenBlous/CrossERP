"""从已保存的利润快照确定性生成平衡凭证草稿。"""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import ProfitSnapshot, Store
from crosserp.vouchers.accounts import AccountsConfig
from crosserp.vouchers.model import VoucherDraft, VoucherLineDraft

_CENT = Decimal("0.01")


def build_month_voucher(
    session: Session,
    *,
    store_id: UUID,
    period: str,
    created_by: str,
    accounts: AccountsConfig,
) -> VoucherDraft:
    """按店铺月份快照生成一张凭证。

    费用和退款在利润快照中按利润口径保存为负数, 生成凭证时转成对应的
    借方正数。每个经济事项同时增加/减少平台应收, 因而借贷天然相等。
    """
    store = session.get(Store, store_id)
    if store is None:
        raise LookupError(f"店铺不存在 {store_id}")
    snapshots = list(
        session.scalars(
            select(ProfitSnapshot)
            .where(ProfitSnapshot.store_id == store_id, ProfitSnapshot.period == period)
            .order_by(ProfitSnapshot.internal_sku)
        )
    )
    if not snapshots:
        raise LookupError(f"找不到店铺 {store.name} 的利润快照 {period}")
    revenue = accounts.require("sales_revenue")
    receivable = accounts.require("platform_receivable")
    fee = accounts.require("platform_fee")
    ad = accounts.require("ad_cost")
    refund = accounts.require("refund_revenue")
    lines: list[VoucherLineDraft] = []
    line_no = 1
    for snapshot in snapshots:
        ref = str(snapshot.id)
        lines.extend(
            _pair(
                line_no,
                receivable,
                revenue,
                _display(snapshot.revenue),
                f"销售 {snapshot.internal_sku}",
                ref,
            )
        )
        line_no += 2
        if snapshot.fees:
            lines.extend(
                _pair(
                    line_no,
                    fee,
                    receivable,
                    _display(abs(snapshot.fees)),
                    f"平台费用 {snapshot.internal_sku}",
                    ref,
                )
            )
            line_no += 2
        if snapshot.ads is not None and snapshot.ads != 0 and snapshot.ads_included:
            lines.extend(
                _pair(
                    line_no,
                    ad,
                    receivable,
                    _display(abs(snapshot.ads)),
                    f"广告费 {snapshot.internal_sku}",
                    ref,
                )
            )
            line_no += 2
        if snapshot.refunds:
            lines.extend(
                _pair(
                    line_no,
                    refund,
                    receivable,
                    _display(abs(snapshot.refunds)),
                    f"退款冲减收入 {snapshot.internal_sku}",
                    ref,
                )
            )
            line_no += 2
    draft = VoucherDraft(
        id=None,
        store_id=store_id,
        period=period,
        source_type="month",
        source_id=f"{store.name}:{period}",
        currency=store.currency,
        inputs_hash=_inputs_hash(snapshots),
        accounts_hash=accounts.content_hash,
        created_by=created_by,
        lines=tuple(lines),
    )
    draft.validate_balance()
    return draft


def _pair(
    line_no: int,
    debit_account: object,
    credit_account: object,
    amount: Decimal,
    summary: str,
    source_ref: str,
) -> tuple[VoucherLineDraft, VoucherLineDraft]:
    from crosserp.vouchers.accounts import AccountMapping

    if not isinstance(debit_account, AccountMapping) or not isinstance(
        credit_account, AccountMapping
    ):
        raise TypeError("科目映射类型错误")
    if debit_account.direction not in {"debit", "either"}:
        raise ValueError(f"科目 {debit_account.key} 不能记借方")
    if credit_account.direction not in {"credit", "either"}:
        raise ValueError(f"科目 {credit_account.key} 不能记贷方")
    return (
        VoucherLineDraft(
            line_no,
            debit_account.key,
            debit_account.code,
            debit_account.name,
            amount,
            Decimal(0),
            summary,
            source_ref,
        ),
        VoucherLineDraft(
            line_no + 1,
            credit_account.key,
            credit_account.code,
            credit_account.name,
            Decimal(0),
            amount,
            summary,
            source_ref,
        ),
    )


def _display(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _inputs_hash(snapshots: list[ProfitSnapshot]) -> str:
    payload = [
        {
            "id": str(row.id),
            "inputs_hash": row.inputs_hash,
            "revenue": str(row.revenue),
            "fees": str(row.fees),
            "refunds": str(row.refunds),
            "ads": None if row.ads is None else str(row.ads),
            "ads_included": row.ads_included,
        }
        for row in snapshots
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
