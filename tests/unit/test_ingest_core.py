from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.catalog.ingest import cleanse_batch, land_file, register_mapping_rule
from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import AppUser, CleansingIssue, FileObject, IngestBatch, MappingRule
from crosserp.db.session import make_engine


def test_land_file_deduplicates_and_cleanses_invalid_rows(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'ingest.db'}"
    upgrade_head(database)
    engine = make_engine(database)
    path = tmp_path / "rows.csv"
    path.write_text(
        "orderId,amount,period,direction\nA-1,1.2345,2026-11,借\n,1.23456,2026-11,贷\n",
        encoding="utf-8",
    )
    with Session(engine) as session, session.begin():
        user = AppUser(
            id=uuid4(),
            username="ingest-user",
            display_name="导入用户",
            password_hash="hash",
            password_changed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        session.add(user)
        rule = MappingRule(
            id=uuid4(),
            rule_key="orders",
            rule_version="1",
            kind="column",
            status="active",
            body_json={"required": ["orderId", "amount"], "amountFields": ["amount"]},
            verified=True,
            created_at=datetime.now(UTC),
        )
        session.add(rule)
        file = FileObject(
            id=uuid4(),
            sha256="a" * 64,
            filename=path.name,
            content_type="text/csv",
            size=path.stat().st_size,
            storage_path=str(path),
            uploaded_by=user.id,
            created_at=datetime.now(UTC),
        )
        session.add(file)
        session.flush()
        batch = land_file(
            session, file.id, kind="order", mapping_rule_version="1", created_by=user.id
        )
        assert batch.status == "landed"
        assert session.get(IngestBatch, batch.id) is not None
        same = land_file(
            session, file.id, kind="order", mapping_rule_version="1", created_by=user.id
        )
        assert same.id == batch.id
        cleanse_batch(session, batch.id)
        session.flush()
        refreshed = session.get(IngestBatch, batch.id)
        assert refreshed is not None
        assert refreshed.status == "cleansed"
        assert refreshed.valid_count == 1
        assert refreshed.quarantined_count == 1


def test_register_mapping_rule_rejects_unknown_fields(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'mapping-rule.db'}"
    upgrade_head(database)
    engine = make_engine(database)
    with Session(engine) as session, session.begin():
        with pytest.raises(APIError) as exc_info:
            register_mapping_rule(
                session,
                rule_key="orders",
                rule_version="1",
                kind="column",
                body={"unknown": True},
            )
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_cleanse_rejects_a_malformed_stored_mapping_rule(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'malformed-rule.db'}"
    upgrade_head(database)
    engine = make_engine(database)
    with Session(engine) as session, session.begin():
        rule = MappingRule(
            id=uuid4(),
            rule_key="orders",
            rule_version="bad",
            kind="column",
            status="active",
            body_json={"required": "orderId"},
            verified=True,
            created_at=datetime.now(UTC),
        )
        batch = IngestBatch(
            id=uuid4(),
            connector_id="orders",
            connector_version="1",
            file_name="orders.csv",
            file_sha256="c" * 64,
            imported_at=datetime.now(UTC),
            row_count=0,
            status="landed",
            error_count=0,
            kind="order",
            mapping_rule_version="bad",
        )
        session.add_all([rule, batch])
        session.flush()
        with pytest.raises(APIError) as exc_info:
            cleanse_batch(session, batch.id)
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_json_non_object_row_is_quarantined_with_its_row_number(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'json-rows.db'}"
    upgrade_head(database)
    engine = make_engine(database)
    path = tmp_path / "rows.json"
    path.write_text('[{"orderId":"A-1"}, "bad", {"orderId":"A-2"}]', encoding="utf-8")
    with Session(engine) as session, session.begin():
        user = AppUser(
            id=uuid4(),
            username="json-ingest-user",
            display_name="JSON 导入用户",
            password_hash="hash",
            password_changed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        session.add(user)
        rule = MappingRule(
            id=uuid4(),
            rule_key="orders",
            rule_version="1",
            kind="column",
            status="active",
            body_json={"required": ["orderId"]},
            verified=True,
            created_at=datetime.now(UTC),
        )
        file = FileObject(
            id=uuid4(),
            sha256="b" * 64,
            filename=path.name,
            content_type="application/json",
            size=path.stat().st_size,
            storage_path=str(path),
            uploaded_by=user.id,
            created_at=datetime.now(UTC),
        )
        session.add_all([rule, file])
        session.flush()
        batch = land_file(
            session, file.id, kind="order", mapping_rule_version="1", created_by=user.id
        )
        assert batch.row_count == 3
        cleanse_batch(session, batch.id)
        issue = session.scalar(select(CleansingIssue).where(CleansingIssue.batch_id == batch.id))
        assert issue is not None
        assert issue.row_no == 2
        assert batch.valid_count == 2
        assert batch.quarantined_count == 1
