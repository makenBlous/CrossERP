from pathlib import Path

import pytest

from crosserp.vouchers.accounts import load_accounts


def _write(path: Path, code: str = "1001") -> None:
    path.write_text(
        "accounts:\n"
        "  sales_revenue: {code: '1001', name: '收入', direction: credit}\n"
        f"  platform_fee: {{code: '{code}', name: '平台费', direction: debit}}\n"
        "  ad_cost: {code: '1003', name: '广告', direction: debit}\n"
        "  fx_diff: {code: '6603', name: '汇兑', direction: either}\n"
        "  platform_receivable: {code: '1122', name: '应收', direction: debit}\n",
        encoding="utf-8",
    )


def test_load_accounts_hashes_content_and_rejects_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "accounts.yaml"
    _write(path)
    loaded = load_accounts(path)
    assert loaded.require("sales_revenue").direction == "credit"
    assert len(loaded.content_hash) == 64
    _write(path, "待会计核实-平台费")
    with pytest.raises(ValueError, match="待会计核实"):
        load_accounts(path)


def test_missing_account_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "accounts.yaml"
    path.write_text("accounts: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="科目映射缺少"):
        load_accounts(path)
