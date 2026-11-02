"""随机追加后篡改任意字段。校验必须失败。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from crosserp.audit.log import append, verify_chain
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import AuditHead, AuditLog
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db

_FIELDS = [column.key for column in AuditLog.__table__.columns]
_TOKEN = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)


def _flip(value: str) -> str:
    if not value:
        return "1" * 64
    last = "0" if value[-1] != "0" else "1"
    return value[:-1] + last


def _audit_input() -> st.SearchStrategy[dict[str, object]]:
    return st.fixed_dictionaries(
        {
            "actor_type": st.sampled_from(["user", "agent", "system"]),
            "action": _TOKEN,
            "target_type": st.sampled_from(["sku", "fx_rate", "order"]),
            "target_id": _TOKEN,
            "after_n": st.integers(min_value=0, max_value=1000),
        }
    )


def _reset(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(AuditLog.__table__.delete())
        conn.execute(AuditHead.__table__.delete())


def _replacement(field: str, row: AuditLog) -> object:
    if field == "id":
        return uuid4()
    if field == "seq":
        return int(row.seq) + 1000
    if field == "ts":
        return datetime(2099, 1, 2, tzinfo=UTC)
    if field == "actor_type":
        return "user" if row.actor_type != "user" else "agent"
    if field == "self_approved":
        return not bool(row.self_approved)
    if field in {"prev_hash", "hash"}:
        return _flip(str(getattr(row, field)))
    if field in {"actor_user_id", "approval_id", "approver_id"}:
        return uuid4()
    if field in {"before_json", "after_json"}:
        return {"tampered": True, "field": field}
    return "tampered"


def test_any_field_tamper_breaks_chain(engine: Engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)

    @given(
        records=st.lists(_audit_input(), min_size=1, max_size=30),
        index=st.integers(min_value=0, max_value=29),
        field=st.sampled_from(_FIELDS),
    )
    @settings(max_examples=20, deadline=None)
    def check(records: list[dict[str, object]], index: int, field: str) -> None:
        _reset(engine)
        with session_scope(engine) as session:
            for item in records:
                append(
                    session,
                    str(item["actor_type"]),
                    str(item["action"]),
                    str(item["target_type"]),
                    str(item["target_id"]),
                    None,
                    {"n": item["after_n"], "name": "保温杯"},
                )
        seq = (index % len(records)) + 1
        with session_scope(engine) as session:
            row = session.scalar(select(AuditLog).where(AuditLog.seq == seq))
            assert row is not None
            value = _replacement(field, row)
            session.execute(update(AuditLog).where(AuditLog.seq == seq).values(**{field: value}))
        with session_scope(engine) as session:
            result = verify_chain(session)
        assert result.ok is False, result

    try:
        check()
    finally:
        downgrade_base(url)
