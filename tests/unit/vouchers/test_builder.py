from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from crosserp.db.schema import ProfitSnapshot, Store
from crosserp.db.session import session_scope
from crosserp.vouchers.accounts import load_accounts
from crosserp.vouchers.builder import build_month_voucher


def _accounts(path: Path) -> None:
    path.write_text(
        "accounts:\n"
        "  sales_revenue: {code: '6001', name: '收入', direction: credit}\n"
        "  platform_fee: {code: '6601', name: '平台费', direction: debit}\n"
        "  ad_cost: {code: '6602', name: '广告', direction: debit}\n"
        "  fx_diff: {code: '6603', name: '汇兑', direction: either}\n"
        "  platform_receivable: {code: '1122', name: '应收', direction: either}\n"
        "  refund_revenue: {code: '6001R', name: '收入冲减', direction: debit}\n",
        encoding="utf-8",
    )


def test_build_month_voucher_is_balanced(engine, tmp_path: Path) -> None:
    from crosserp.db.migrate import upgrade_head

    upgrade_head(engine.url.render_as_string(hide_password=False))
    accounts_path = tmp_path / "accounts.yaml"
    _accounts(accounts_path)
    with session_scope(engine) as session:
        store = Store(
            id=uuid4(), platform="shopify", marketplace="US", name="builder", currency="USD"
        )
        session.add(store)
        session.flush()
        session.add(
            ProfitSnapshot(
                id=uuid4(),
                store_id=store.id,
                period="2026-10",
                internal_sku="S1",
                revenue=Decimal("10"),
                fees=Decimal("-1.25"),
                refunds=Decimal("-2"),
                cogs=Decimal("0"),
                freight=Decimal("0"),
                ads=None,
                currency="USD",
                calc_version="test",
                inputs_hash="a" * 64,
                qty_sold=1,
                qty_refunded=1,
                qty_net=0,
                promotion=Decimal("0"),
                fx_rate=None,
                profit_cny=None,
                ads_included=False,
                status="ok",
                recon_run_id=None,
            )
        )
        draft = build_month_voucher(
            session,
            store_id=store.id,
            period="2026-10",
            created_by="maken",
            accounts=load_accounts(accounts_path),
        )
        draft.validate_balance()
        assert draft.total_debit == draft.total_credit == Decimal("13.25")
        assert all(not (line.debit and line.credit) for line in draft.lines)
