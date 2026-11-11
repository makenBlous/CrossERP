from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from crosserp.catalog.ingest import cleanse_batch, land_file
from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import AppUser, FileObject, IngestBatch, MappingRule
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
