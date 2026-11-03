"""异常目录写入服务的去重和严重度。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from crosserp.core.enums import IssueKind
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Issue
from crosserp.db.session import session_scope
from crosserp.issues.service import open_issue

pytestmark = pytest.mark.db


def test_open_issue_deduplicates_source_ref(engine: Engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    try:
        upgrade_head(url)
        with session_scope(engine) as session:
            first = open_issue(
                session,
                IssueKind.UNKNOWN_FEE_TYPE,
                store_id=None,
                period="2026-10",
                source_ref="input.tsv:4:UNKNOWN_FEE_TYPE",
                detail={"source_file": "input.tsv", "row_no": 4},
            )
            second = open_issue(
                session,
                IssueKind.UNKNOWN_FEE_TYPE,
                store_id=None,
                period="2026-10",
                source_ref="input.tsv:4:UNKNOWN_FEE_TYPE",
                detail={"source_file": "input.tsv", "row_no": 4},
            )
            assert second.id == first.id
            assert second.severity == "warn"
            assert session.scalar(select(func.count()).select_from(Issue)) == 1
    finally:
        downgrade_base(url)
