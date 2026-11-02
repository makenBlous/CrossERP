"""测试夹具。未设置 CROSSERP_TEST_DATABASE_URL 时用临时 SQLite 文件。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import MetaData
from sqlalchemy.engine import URL, Engine

from crosserp.db.session import make_engine


def _sqlite_file_url(path: Path) -> str:
    resolved = path.resolve()
    return URL.create(drivername="sqlite", database=str(resolved)).render_as_string(
        hide_password=False
    )


def _drop_probe_tables(engine: Engine) -> None:
    metadata = MetaData()
    metadata.reflect(engine, only=lambda name, _meta: name.startswith("t04_"))
    metadata.drop_all(engine)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    """每个测试一个引擎。结束后丢掉本任务建的临时表。"""
    url = os.environ.get("CROSSERP_TEST_DATABASE_URL")
    if url:
        database = make_engine(url)
    else:
        database = make_engine(_sqlite_file_url(tmp_path / "crosserp-test.db"))
    try:
        yield database
    finally:
        _drop_probe_tables(database)
        database.dispose()
