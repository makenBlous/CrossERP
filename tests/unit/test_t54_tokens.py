"""T54 API token 生命周期覆盖。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from crosserp.auth import tokens


def test_token_create_authenticate_revoke(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), username="tester", is_active=True)
    events: list[object] = []

    class Session:
        def __init__(self) -> None:
            self.row = None

        def add(self, row: object) -> None:
            self.row = row

        def flush(self) -> None:
            return None

        def scalar(self, _statement: object) -> object:
            return self.row

        def get(self, _model: object, _id: object) -> object:
            return user if _model is tokens.AppUser else self.row

    monkeypatch.setattr(tokens, "record_security", lambda *args, **kwargs: events.append(args))
    session = Session()
    row, plain = tokens.create_token(session, user, name="test")
    row.user_id = user.id
    assert plain.startswith("cerp_")
    assert tokens.authenticate(session, plain)[1] is user
    assert tokens.revoke_token(session, row.id, user)
    assert not tokens.revoke_token(session, row.id, user)
    assert len(events) == 2


def test_token_rejects_expired_and_inactive(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), username="tester", is_active=False)
    row = SimpleNamespace(
        token_hash=hashlib.sha256(b"plain").hexdigest(),
        revoked_at=None,
        created_at=datetime.now(UTC) - timedelta(days=91),
        user_id=user.id,
    )

    class Session:
        def scalar(self, _statement: object) -> object:
            return row

        def get(self, _model: object, _id: object) -> object:
            return user

    assert tokens.authenticate(Session(), "plain") is None
