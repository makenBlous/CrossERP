from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AppUser
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.iam.service import IAMService


def test_iam_state_survives_service_restart_and_version_bumps(tmp_path: Path) -> None:
    url = sqlite_file_url(tmp_path / "iam.db")
    upgrade_head(url)
    engine = make_engine(url)
    user_id = uuid4()
    try:
        with Session(engine) as session, session.begin():
            session.add(
                AppUser(
                    id=user_id,
                    username="iam-persist",
                    display_name="IAM",
                    password_hash="x",
                    is_active=True,
                    failed_logins=0,
                    password_changed_at=datetime.now(UTC),
                    must_change_password=False,
                    created_at=datetime.now(UTC),
                    permission_version=0,
                )
            )
        first = IAMService(engine)
        first.assign_role(user_id, "viewer")
        first.set_override(user_id, "report:read", effect="deny", reason="sod")
        first.set_temporary_grant(
            user_id, "issue:write", expires_at=datetime.now(UTC) + timedelta(hours=1)
        )
        assert first.permission_version(user_id) == 3
        second = IAMService(engine)
        decision = second.effective_permission(user_id, "report:read")
        assert not decision.allowed
        assert second.effective_permission(user_id, "issue:write").allowed
        second.update_role("viewer", active=False)
        assert second.permission_version(user_id) == 4
    finally:
        engine.dispose()
        downgrade_base(url)
