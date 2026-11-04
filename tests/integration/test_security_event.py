from datetime import UTC, datetime

from crosserp.audit.security import SecurityEventName, record, verify_security_chain
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import SecurityEvent
from crosserp.db.session import session_scope


def test_security_chain_records_and_detects_tampering(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            record(
                session,
                SecurityEventName.LOGIN_FAILED,
                username="someone",
                detail={"ok": False},
                ts=datetime.now(UTC),
            )
            assert verify_security_chain(session)
            row = session.query(SecurityEvent).one()
            row.username = "tampered"
            assert not verify_security_chain(session)
    finally:
        downgrade_base(url)
