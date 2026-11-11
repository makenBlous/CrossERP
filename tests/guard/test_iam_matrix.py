from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AppUser, UserRole
from crosserp.iam.service import IAMService
from crosserp.platform.principal import ActorType, Principal

DATA = json.loads(
    (Path(__file__).parent / "data" / "iam_route_matrix.json").read_text(encoding="utf8")
)


def test_all_21_roles_cover_all_35_routes_and_ai_cap(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    service = IAMService(engine)
    rows = DATA["rows"]
    try:
        assert len({row["role"] for row in rows}) == 21
        assert len({(row["method"], row["path"]) for row in rows}) == 35
        for row in rows:
            user_id = uuid4()
            with Session(engine) as session, session.begin():
                session.add(
                    AppUser(
                        id=user_id,
                        username=f"matrix-{user_id.hex[:12]}",
                        display_name="IAM matrix",
                        password_hash="x",
                        is_active=True,
                        failed_logins=0,
                        locked_until=None,
                        password_changed_at=datetime.now(UTC),
                        must_change_password=False,
                        created_at=datetime.now(UTC),
                        permission_version=0,
                    )
                )
                session.add(
                    UserRole(user_id=user_id, role=row["role"], granted_at=datetime.now(UTC))
                )
            human = Principal(user_id=user_id, roles=frozenset({row["role"]}))
            allowed = service.effective_permission(
                user_id, row["permission"], principal=human
            ).allowed
            assert row["human"] == (200 if allowed else 404), row
            agent = Principal(
                user_id=user_id,
                roles=frozenset({row["role"]}),
                actor_type=ActorType.AGENT,
                agent_id="matrix",
                on_behalf_of=user_id,
            )
            if row["riskTier"] == "critical":
                assert row["aiOn"] == 403
            else:
                ai_allowed = service.effective_permission(
                    user_id, row["permission"], principal=agent
                ).allowed
                assert row["aiOn"] == (200 if ai_allowed else 404)
            assert row["aiOff"] == row["aiOn"]
    finally:
        downgrade_base(url)
