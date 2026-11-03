"""合成样本三库对账验收。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.db.migrate import downgrade_base
from crosserp.db.schema import Issue, ReconRun
from crosserp.db.session import session_scope
from crosserp.recon.engine import reconcile_all

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[2]


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_reconcile_synthetic_matches_expected_and_preserves_runs(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    expected = json.loads(
        (ROOT / "samples" / "synthetic" / "expected" / "summary.json").read_text(encoding="utf-8")
    )
    try:
        assert CliRunner().invoke(app, ["init"]).exit_code == 0
        imported = CliRunner().invoke(app, ["demo-import"])
        assert imported.exit_code == 0, imported.output
        with session_scope(engine) as session:
            first = reconcile_all(session, "2026-10")
            active = [item for item in first if item.groups_total]
            assert sum(item.groups_total for item in active) == expected["order_type_group_count"]
            assert (
                sum(item.groups_matched for item in active)
                == expected["matched_order_type_group_count"]
            )
            assert sum(item.groups_total - item.groups_matched for item in active) == 6
            run_ids = [item.run_id for item in first]
            kinds = [
                issue.kind
                for issue in session.scalars(select(Issue).where(Issue.recon_run_id.in_(run_ids)))
            ]
            assert kinds.count("FEE_OVERCHARGE") == 1
            assert kinds.count("SETTLEMENT_DELAYED") == 3
            assert kinds.count("CHARGEBACK") == 2
            assert kinds.count("PARTIAL_REFUND") == 1
            assert "DUPLICATE_SETTLEMENT" not in kinds
            second = reconcile_all(session, "2026-10")
            assert [item.groups_matched for item in second] == [
                item.groups_matched for item in first
            ]
            assert session.scalar(select(func.count()).select_from(ReconRun)) == len(first) * 2
    finally:
        downgrade_base(url)
