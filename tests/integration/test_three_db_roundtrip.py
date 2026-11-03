"""跨 SQLite、MySQL 8.4 和 PostgreSQL 18 的三库往返验收。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.engine import Engine

from crosserp.db.migrate import check_schema, downgrade_base, upgrade_head
from crosserp.db.types import FxRate, Money4, UtcDateTime

pytestmark = pytest.mark.db

_BEIJING = timezone(timedelta(hours=8))
_MONEY_VALUES = (
    Decimal("0.0001"),
    Decimal("-0.0001"),
    Decimal("922337203685477.5807"),
    Decimal("-922337203685477.5807"),
    Decimal("123456789.1234"),
)


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _probe_table(engine: Engine) -> tuple[MetaData, Table]:
    metadata = MetaData()
    table = Table(
        "t16_three_db_roundtrip",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Money4(), nullable=False),
        Column("rate", FxRate(), nullable=False),
        Column("happened_at", UtcDateTime(), nullable=False),
        Column("title", String(255), nullable=False),
    )
    metadata.create_all(engine)
    return metadata, table


def test_migration_roundtrip_is_portable(engine: Engine) -> None:
    url = _url(engine)
    try:
        upgrade_head(url)
        check_schema(url)
        downgrade_base(url)
        upgrade_head(url)
        check_schema(url)
    finally:
        downgrade_base(url)


@pytest.mark.parametrize("amount", _MONEY_VALUES)
def test_money4_extreme_values_roundtrip(engine: Engine, amount: Decimal) -> None:
    metadata, table = _probe_table(engine)
    try:
        with engine.begin() as connection:
            connection.execute(
                table.insert().values(
                    id=1,
                    amount=amount,
                    rate=Decimal("7.12345678"),
                    happened_at=datetime(2026, 11, 9, 8, 0, tzinfo=_BEIJING),
                    title="保温杯 🍵 黑色 500ml",
                )
            )
        with engine.connect() as connection:
            row = connection.execute(select(table)).one()
        assert row.amount == amount
        assert row.rate == Decimal("7.12345678")
        assert row.happened_at == datetime(2026, 11, 9, 0, 0, tzinfo=UTC)
        assert row.title == "保温杯 🍵 黑色 500ml"
    finally:
        metadata.drop_all(engine)
