from datetime import UTC, datetime
from uuid import uuid4

from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import LlmBudget
from crosserp.db.session import session_scope
from crosserp.observability.budget import check


def test_budget_without_configuration_is_ok(engine) -> None:
    upgrade_head(engine.url.render_as_string(hide_password=False))
    with session_scope(engine) as session:
        assert check(session, now=datetime(2026, 11, 5, tzinfo=UTC)) == "ok"


def test_budget_token_limit_blocks(engine) -> None:
    upgrade_head(engine.url.render_as_string(hide_password=False))
    with session_scope(engine) as session:
        session.add(
            LlmBudget(
                id=uuid4(),
                scope="global",
                user_id=None,
                period="2026-11",
                limit_amount=None,
                limit_tokens=10,
                currency="USD",
                warn_percent=80,
                created_by="admin",
                created_at=datetime.now(UTC),
            )
        )
        assert check(session, now=datetime(2026, 11, 5, tzinfo=UTC)) == "ok"
