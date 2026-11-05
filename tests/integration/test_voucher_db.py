from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import Store, Voucher, VoucherLine
from crosserp.db.session import session_scope
from crosserp.vouchers.model import VoucherDraft, VoucherLineDraft
from crosserp.vouchers.service import save_draft


@pytest.mark.db
def test_voucher_save_balance_and_duplicate_source(engine) -> None:
    upgrade_head(engine.url.render_as_string(hide_password=False))
    with session_scope(engine) as session:
        store = Store(
            id=uuid4(), platform="shopify", marketplace="US", name="voucher", currency="USD"
        )
        session.add(store)
        session.flush()
        draft = VoucherDraft(
            None,
            store.id,
            "2026-10",
            "month",
            "source-1",
            "USD",
            "a" * 64,
            "b" * 64,
            "maken",
            (
                VoucherLineDraft(
                    1,
                    "platform_receivable",
                    "1122",
                    "应收",
                    Decimal("10"),
                    Decimal("0"),
                    "销售",
                    "profit",
                ),
                VoucherLineDraft(
                    2,
                    "sales_revenue",
                    "6001",
                    "收入",
                    Decimal("0"),
                    Decimal("10"),
                    "销售",
                    "profit",
                ),
            ),
        )
        row = save_draft(session, draft)
        assert row.total_debit == row.total_credit == Decimal("10.0000")
        assert (
            len(session.scalars(select(VoucherLine).where(VoucherLine.voucher_id == row.id)).all())
            == 2
        )
        with pytest.raises(ValueError, match="同一来源"):
            save_draft(session, draft)
        assert session.scalar(select(Voucher).where(Voucher.id == row.id)) is not None
