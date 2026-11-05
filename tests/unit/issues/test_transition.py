from uuid import uuid4

import pytest

from crosserp.core.enums import IssueStatus
from crosserp.db.schema import Issue
from crosserp.issues.service import transition


def test_issue_transition_requires_note(engine) -> None:
    from datetime import UTC, datetime

    from crosserp.db.migrate import downgrade_base, upgrade_head
    from crosserp.db.session import session_scope

    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = Issue(
                id=uuid4(),
                kind="PARSE_ERROR",
                severity="error",
                detail_json={},
                status="open",
                created_at=datetime.now(UTC),
            )
            session.add(row)
            session.flush()
            with pytest.raises(ValueError):
                transition(session, row.id, IssueStatus.IGNORED, "no")
            transition(session, row.id, IssueStatus.IGNORED, "这是足够长的说明")
            assert row.status == "ignored"
    finally:
        downgrade_base(url)
