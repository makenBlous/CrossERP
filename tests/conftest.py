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


@pytest.fixture(scope="session", autouse=True)
def isolate_default_database(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """测试进程默认使用本次测试专用 SQLite, 不触碰用户 home 数据库。"""
    if os.environ.get("CROSSERP_TEST_DATABASE_URL", "").startswith(("mysql", "postgres")):
        if not os.environ.get("CROSSERP_FILES_DIR"):
            os.environ["CROSSERP_FILES_DIR"] = str(tmp_path_factory.mktemp("crosserp-files"))
        yield
        return
    database = _sqlite_file_url(tmp_path_factory.mktemp("crosserp-session") / "data.db")
    files_dir = tmp_path_factory.mktemp("crosserp-files")
    previous_database = os.environ.get("CROSSERP_DATABASE_URL")
    previous_migrate = os.environ.get("CROSSERP_MIGRATE_DATABASE_URL")
    previous_files = os.environ.get("CROSSERP_FILES_DIR")
    os.environ["CROSSERP_DATABASE_URL"] = database
    os.environ["CROSSERP_MIGRATE_DATABASE_URL"] = database
    os.environ["CROSSERP_FILES_DIR"] = str(files_dir)
    try:
        yield
    finally:
        if previous_database is None:
            os.environ.pop("CROSSERP_DATABASE_URL", None)
        else:
            os.environ["CROSSERP_DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("CROSSERP_MIGRATE_DATABASE_URL", None)
        else:
            os.environ["CROSSERP_MIGRATE_DATABASE_URL"] = previous_migrate
        if previous_files is None:
            os.environ.pop("CROSSERP_FILES_DIR", None)
        else:
            os.environ["CROSSERP_FILES_DIR"] = previous_files


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
