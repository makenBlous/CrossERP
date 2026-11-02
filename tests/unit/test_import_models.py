"""导入层模型拒绝 float 和无时区时间。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from crosserp.core.enums import ImportStatus
from crosserp.core.models import FxRateRecord, ImportBatchRecord


def test_fx_rate_record_rejects_float() -> None:
    with pytest.raises(ValidationError, match="float"):
        FxRateRecord(
            id=uuid4(),
            period="2026-11",
            from_ccy="USD",
            to_ccy="CNY",
            rate=7.1,  # type: ignore[arg-type]
            source="manual",
        )


def test_import_batch_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="时区"):
        ImportBatchRecord(
            id=uuid4(),
            connector_id="fake",
            connector_version="0",
            file_name="a.csv",
            file_sha256="a" * 64,
            imported_at=datetime(2026, 11, 2),
            row_count=1,
            status=ImportStatus.RUNNING,
            error_count=0,
        )


def test_import_batch_accepts_aware_datetime() -> None:
    record = ImportBatchRecord(
        id=uuid4(),
        connector_id="fake",
        connector_version="0",
        file_name="a.csv",
        file_sha256="b" * 64,
        imported_at=datetime(2026, 11, 2, tzinfo=UTC),
        row_count=1,
        status=ImportStatus.DONE,
        error_count=0,
    )
    assert record.row_count == 1
    assert record.status is ImportStatus.DONE
