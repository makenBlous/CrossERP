from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from crosserp.iam.service import IAMService
from crosserp.platform.principal import ActorType, Principal

DATA = json.loads(
    (Path(__file__).parent / "data" / "iam_route_matrix.json").read_text(encoding="utf8")
)


def test_all_21_roles_cover_all_35_routes_and_ai_cap() -> None:
    service = IAMService()
    rows = DATA["rows"]
    assert len({row["role"] for row in rows}) == 21
    assert len({(row["method"], row["path"]) for row in rows}) == 35
    for row in rows:
        user_id = uuid4()
        human = Principal(user_id=user_id, roles=frozenset({row["role"]}))
        allowed = service.effective_permission(user_id, row["permission"], principal=human).allowed
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
