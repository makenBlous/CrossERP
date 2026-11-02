"""任意 4 位小数 Decimal 在 SQLite 上往返相等。"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import Column, Integer, MetaData, Table, select
from sqlalchemy.engine import URL, Engine

from crosserp.db.session import make_engine
from crosserp.db.types import Money4

pytestmark = pytest.mark.db

# SQLite INTEGER 是 64 位。万分位上限按任务规定取对称值。
SQLITE_MONEY4_MAX = Decimal("922337203685477.5807")

amounts = st.decimals(
    min_value=-SQLITE_MONEY4_MAX,
    max_value=SQLITE_MONEY4_MAX,
    places=4,
    allow_nan=False,
    allow_infinity=False,
)


def _sqlite_file_url(path: Path) -> str:
    return URL.create(drivername="sqlite", database=str(path.resolve())).render_as_string(
        hide_password=False
    )


@pytest.fixture(scope="module")
def sqlite_money4() -> Iterator[tuple[Engine, Table]]:
    directory = Path(tempfile.mkdtemp(prefix="crosserp-money4-"))
    engine = make_engine(_sqlite_file_url(directory / "prop.db"))
    metadata = MetaData()
    table = Table(
        "t04_money4_prop",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Money4(), nullable=False),
    )
    metadata.create_all(engine)
    try:
        yield engine, table
    finally:
        engine.dispose()
        shutil.rmtree(directory, ignore_errors=True)


@settings(deadline=None)
@given(value=amounts)
def test_money4_sqlite_roundtrip(value: Decimal, sqlite_money4: tuple[Engine, Table]) -> None:
    engine, table = sqlite_money4
    with engine.begin() as conn:
        conn.execute(table.delete())
        conn.execute(table.insert().values(id=1, amount=value))
        loaded = conn.execute(select(table.c.amount)).scalar_one()
        raw = conn.exec_driver_sql("SELECT amount FROM t04_money4_prop").scalar_one()
    assert isinstance(loaded, Decimal)
    assert loaded == value
    assert str(loaded) == f"{value:.4f}"
    assert isinstance(raw, int)
    assert raw == int(value * 10000)
