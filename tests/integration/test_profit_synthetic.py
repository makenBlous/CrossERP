"""Synthetic profit persistence and idempotence."""

from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import downgrade_base
from crosserp.db.schema import ProfitSnapshot, Store
from crosserp.db.session import session_scope
from crosserp.profit.service import compute_and_save

pytestmark = pytest.mark.db


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_profit_synthetic_is_deterministic_and_has_missing_cost_status(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    try:
        assert CliRunner().invoke(app, ["init"]).exit_code == 0
        imported = CliRunner().invoke(app, ["demo-import"])
        assert imported.exit_code == 0, imported.output
        with session_scope(engine) as session:
            stores = list(session.scalars(select(Store).order_by(Store.name)))
            reports = [compute_and_save(session, store.id, "2026-10") for store in stores]
            assert any(report.sku_profits for report in reports)
            assert any(
                item.status == "cost_missing" for report in reports for item in report.sku_profits
            )
            before = session.scalar(select(func.count()).select_from(ProfitSnapshot))
            again = [compute_and_save(session, store.id, "2026-10") for store in stores]
            after = session.scalar(select(func.count()).select_from(ProfitSnapshot))
            assert before == after
            assert [report.store_profit for report in reports] == [
                report.store_profit for report in again
            ]
    finally:
        with session_scope(engine) as session:
            session.execute(delete(ProfitSnapshot))
        downgrade_base(url)
