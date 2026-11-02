"""随机平衡的 Amazon 结算文件。导入后明细合计等于总额。"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.connectors.amazon_settlement_v2 import AmazonSettlementV2Connector
from crosserp.connectors.importer import import_file
from crosserp.core.enums import ImportStatus
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Settlement, SettlementLine
from crosserp.db.session import make_engine, session_scope, sqlite_file_url

pytestmark = pytest.mark.db

_COLUMNS = (
    "settlement-id",
    "settlement-start-date",
    "settlement-end-date",
    "deposit-date",
    "total-amount",
    "currency",
    "transaction-type",
    "marketplace-name",
    "amount-type",
    "amount-description",
    "amount",
    "order-id",
    "sku",
    "quantity-purchased",
)
_CENTS = Decimal("0.01")


_CALLS = 0


def _format_amount(amount: Decimal, locale: str) -> str:
    quantized = amount.quantize(_CENTS)
    sign = "-" if quantized < 0 else ""
    text = format(abs(quantized), "f")
    whole, frac = text.split(".", 1)
    body = f"{whole}.{(frac + '00')[:2]}"
    if locale == "eu":
        return sign + body.replace(".", ",")
    return sign + body


def _write_balanced(
    path: Path,
    *,
    settlement_id: str,
    amounts: list[Decimal],
    locale: str,
) -> Decimal:
    currency = "EUR" if locale == "eu" else "USD"
    marketplace = "Amazon.de" if locale == "eu" else "Amazon.com"
    total = Decimal("0")
    for amount in amounts:
        total += amount
    rows: list[dict[str, str]] = [
        {
            "settlement-id": settlement_id,
            "settlement-start-date": "2026-10-01",
            "settlement-end-date": "2026-10-14",
            "deposit-date": "2026-10-16",
            "total-amount": _format_amount(total, locale),
            "currency": currency,
            "transaction-type": "",
            "marketplace-name": marketplace,
            "amount-type": "",
            "amount-description": "",
            "amount": "",
            "order-id": "",
            "sku": "",
            "quantity-purchased": "",
        }
    ]
    for index, amount in enumerate(amounts, start=1):
        rows.append(
            {
                "settlement-id": settlement_id,
                "settlement-start-date": "2026-10-01",
                "settlement-end-date": "2026-10-14",
                "deposit-date": "2026-10-16",
                "total-amount": "",
                "currency": currency,
                "transaction-type": "Order",
                "marketplace-name": marketplace,
                "amount-type": "ItemPrice",
                "amount-description": "Principal",
                "amount": _format_amount(amount, locale),
                "order-id": f"{settlement_id}-{index}",
                "sku": "SKU-1",
                "quantity-purchased": "1",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
            quoting=csv.QUOTE_NONE,
        )
        writer.writeheader()
        writer.writerows(rows)
    return total


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    amounts=st.lists(
        st.decimals(
            min_value=Decimal("-1000"),
            max_value=Decimal("1000"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=6,
    ),
    use_eu=st.booleans(),
)
def test_amazon_random_balanced_file_sums(
    tmp_path: Path,
    amounts: list[Decimal],
    use_eu: bool,
) -> None:
    global _CALLS
    _CALLS += 1
    locale = "eu" if use_eu else "us"
    settlement_id = f"P-{_CALLS}"
    path = tmp_path / f"{settlement_id}.tsv"
    expected = _write_balanced(
        path,
        settlement_id=settlement_id,
        amounts=amounts,
        locale=locale,
    )
    database = make_engine(sqlite_file_url(tmp_path / f"{settlement_id}.db"))
    url = database.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(database) as session:
            result = import_file(session, path, AmazonSettlementV2Connector())
            assert result.status is ImportStatus.DONE, result.message
            _assert_sum(session, settlement_id, expected)
    finally:
        downgrade_base(url)
        database.dispose()


def _assert_sum(session: Session, settlement_id: str, expected: Decimal) -> None:
    settlement = session.scalar(select(Settlement).where(Settlement.external_id == settlement_id))
    assert settlement is not None
    assert settlement.total == expected
    lines = session.scalars(
        select(SettlementLine).where(SettlementLine.settlement_id == settlement.id)
    ).all()
    total = Decimal("0")
    for line in lines:
        total += line.amount
    assert total == settlement.total
    assert total == expected
