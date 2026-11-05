from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import ProfitSnapshot, Store
from crosserp.db.session import make_engine, session_scope, sqlite_file_url


def test_read_only_profit_tool_returns_citations(tmp_path: Path, monkeypatch) -> None:
    url = sqlite_file_url(tmp_path / "agent.sqlite")
    upgrade_head(url)
    store_id = uuid4()
    with session_scope(make_engine(url)) as session:
        session.add(
            Store(id=store_id, platform="shopify", marketplace="US", name="agent", currency="USD")
        )
        session.flush()
        session.add(
            ProfitSnapshot(
                id=uuid4(),
                store_id=store_id,
                period="2026-10",
                internal_sku="SKU-1",
                revenue=Decimal("10"),
                fees=Decimal("1"),
                refunds=Decimal("0"),
                cogs=Decimal("2"),
                freight=Decimal("0"),
                ads=None,
                profit=Decimal("7"),
                currency="USD",
                calc_version="test",
                inputs_hash="a" * 64,
                qty_sold=1,
                qty_refunded=0,
                qty_net=1,
                promotion=Decimal("0"),
                fx_rate=None,
                profit_cny=None,
                ads_included=False,
                status="ok",
                recon_run_id=None,
            )
        )
    monkeypatch.setenv("CROSSERP_AGENT_DATABASE_URL", url)
    from crosserp.agent.tools import compare_profit, get_profit

    result = get_profit("agent", "2026-10")
    assert result.data[0]["profit"] == "7.0000"
    assert result.citations[0].table == "profit_snapshot"
    assert compare_profit("agent", "2026-10", "2026-10").data[0]["difference"] == "0.0000"


def test_tool_limits() -> None:
    import pytest

    from crosserp.agent.tools import list_issues

    with pytest.raises(ValueError):
        list_issues(limit=201)
