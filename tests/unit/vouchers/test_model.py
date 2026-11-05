from decimal import Decimal
from uuid import uuid4

import pytest

from crosserp.vouchers.model import VoucherDraft, VoucherLineDraft


def _line(debit: str, credit: str) -> VoucherLineDraft:
    return VoucherLineDraft(1, "x", "1001", "测试", Decimal(debit), Decimal(credit), "摘要", "src")


def test_line_only_has_one_side_and_draft_balances() -> None:
    with pytest.raises(ValueError):
        _line("1", "1")
    draft = VoucherDraft(
        uuid4(),
        uuid4(),
        "2026-10",
        "month",
        "demo",
        "CNY",
        "a" * 64,
        "b" * 64,
        "maken",
        (_line("1", "0"), _line("0", "1")),
    )
    draft.validate_balance()
    assert draft.total_debit == draft.total_credit == Decimal("1")


def test_unbalanced_draft_rejected() -> None:
    draft = VoucherDraft(
        None,
        uuid4(),
        "2026-10",
        "month",
        "demo",
        "CNY",
        "a" * 64,
        "b" * 64,
        "maken",
        (_line("2", "0"), _line("0", "1")),
    )
    with pytest.raises(ValueError, match="借贷不平"):
        draft.validate_balance()
