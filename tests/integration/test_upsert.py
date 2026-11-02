"""同一汇率键 upsert 两次。只留一行。汇率是第二次的值。"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from crosserp.db.dialects import upsert
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.repo.fx import get_fx_rate, upsert_fx_rate
from crosserp.db.repo.stores import get_store, upsert_store
from crosserp.db.schema import FxRate
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_fx_rate_upsert_keeps_second_rate(engine: Engine) -> None:
    url = _url(engine)
    try:
        upgrade_head(url)
        first_id = uuid4()
        second_id = uuid4()
        with session_scope(engine) as session:
            upsert(
                session,
                FxRate.__table__,
                {
                    "id": first_id,
                    "period": "2026-11",
                    "from_ccy": "USD",
                    "to_ccy": "CNY",
                    "rate": Decimal("7.10000000"),
                    "source": "manual",
                },
                ["period", "from_ccy", "to_ccy"],
                ["rate", "source"],
            )
            upsert(
                session,
                FxRate.__table__,
                {
                    "id": second_id,
                    "period": "2026-11",
                    "from_ccy": "USD",
                    "to_ccy": "CNY",
                    "rate": Decimal("7.25000000"),
                    "source": "revised",
                },
                ["period", "from_ccy", "to_ccy"],
                ["rate", "source"],
            )
        with session_scope(engine) as session:
            count = session.scalar(select(func.count()).select_from(FxRate))
            row = get_fx_rate(session, "2026-11", "USD", "CNY")
            assert count == 1
            assert row is not None
            assert row.id == first_id
            assert row.rate == Decimal("7.25000000")
            assert row.source == "revised"
    finally:
        downgrade_base(url)


def test_store_repo_upsert(engine: Engine) -> None:
    url = _url(engine)
    store_id = uuid4()
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            upsert_store(
                session,
                store_id=store_id,
                platform="amazon",
                marketplace="amazon.com",
                name="旧店名",
                currency="USD",
            )
            upsert_fx_rate(
                session,
                rate_id=uuid4(),
                period="2026-11",
                from_ccy="EUR",
                to_ccy="CNY",
                rate=Decimal("7.80000000"),
                source="sheet",
            )
        with session_scope(engine) as session:
            upsert_store(
                session,
                store_id=store_id,
                platform="amazon",
                marketplace="amazon.com",
                name="新店名",
                currency="USD",
            )
            upsert_fx_rate(
                session,
                rate_id=uuid4(),
                period="2026-11",
                from_ccy="EUR",
                to_ccy="CNY",
                rate=Decimal("7.81000000"),
                source="sheet",
            )
            store = get_store(session, store_id)
            rate = get_fx_rate(session, "2026-11", "EUR", "CNY")
            assert store is not None
            assert store.name == "新店名"
            assert rate is not None
            assert rate.rate == Decimal("7.81000000")
    finally:
        downgrade_base(url)
