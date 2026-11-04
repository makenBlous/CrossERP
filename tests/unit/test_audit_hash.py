"""哈希链规范化。固定输入对应固定 hash。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from crosserp.audit.chain import GENESIS_PREV_HASH, canonical_json, compute_hash
from crosserp.audit.log import payload_from_log
from crosserp.db.schema import AuditLog

_PINNED_HASH = "07efa045647b75020e5f238b8343211ca73606782fe04d93f9ca4b0615a8f462"


def test_genesis_prev_hash_is_64_zeros() -> None:
    assert GENESIS_PREV_HASH == "0" * 64
    assert len(GENESIS_PREV_HASH) == 64


def test_canonical_json_sorts_keys_and_keeps_chinese() -> None:
    assert canonical_json({"b": 1, "a": "保温杯"}) == '{"a":"保温杯","b":1}'.encode()


def test_decimal_and_datetime_are_utc_strings() -> None:
    moment = datetime(2026, 11, 2, 8, 0, tzinfo=timezone(timedelta(hours=8)))
    raw = canonical_json({"amount": Decimal("12.50"), "ts": moment, "name": "保温杯"})
    expected = '{"amount":"12.50","name":"保温杯","ts":"2026-11-02T00:00:00.000000+00:00"}'
    assert raw == expected.encode()


def test_compute_hash_is_pinned() -> None:
    record = {
        "action": "import",
        "actor_type": "system",
        "after": {"amount": Decimal("12.50"), "sku": "保温杯"},
        "before": None,
        "seq": 1,
    }
    assert compute_hash(GENESIS_PREV_HASH, record) == _PINNED_HASH


def test_key_order_does_not_change_hash() -> None:
    assert compute_hash(GENESIS_PREV_HASH, {"b": 1, "a": 2}) == compute_hash(
        GENESIS_PREV_HASH, {"a": 2, "b": 1}
    )


def test_float_is_rejected() -> None:
    with pytest.raises(TypeError):
        canonical_json({"amount": 1.25})


def test_payload_covers_every_column_except_hash() -> None:
    row = AuditLog(
        id=uuid4(),
        seq=1,
        ts=datetime(2026, 11, 2, tzinfo=UTC),
        actor_type="system",
        actor_name="system",
        action="import",
        target_type="sku",
        target_id="1",
        self_approved=False,
        prev_hash=GENESIS_PREV_HASH,
        hash=GENESIS_PREV_HASH,
        hash_version=2,
    )
    columns = {column.key for column in AuditLog.__table__.columns}
    assert set(payload_from_log(row)) == columns - {"hash"}


def test_old_hash_payload_omits_new_context_fields() -> None:
    row = AuditLog(
        id=uuid4(),
        seq=1,
        ts=datetime(2026, 11, 2, tzinfo=UTC),
        actor_type="system",
        actor_name=None,
        action="import",
        target_type="batch",
        target_id="1",
        self_approved=False,
        prev_hash=GENESIS_PREV_HASH,
        hash=GENESIS_PREV_HASH,
        hash_version=1,
    )
    payload = payload_from_log(row)
    assert "actor_name" not in payload
    assert "hash_version" not in payload
