"""MySQL 启动自检。没有 MySQL 时跳过需要真服务器的用例。"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from crosserp.core.errors import DatabaseConfigError
from crosserp.db.dialects import check_server, mysql_config_error, postgres_version_warning
from crosserp.db.session import make_engine

pytestmark = pytest.mark.db

_LATIN_DB = "crosserp_t04_latin1"


def test_mysql_config_error_messages() -> None:
    old = mysql_config_error("8.0.36", "utf8mb4", "STRICT_TRANS_TABLES", "crosserp")
    assert old is not None
    assert "8.4" in old

    charset = mysql_config_error("8.4.7", "latin1", "STRICT_TRANS_TABLES", "crosserp")
    assert charset is not None
    assert "ALTER DATABASE crosserp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;" in charset

    mode = mysql_config_error("8.4.7", "utf8mb4", "NO_ENGINE_SUBSTITUTION", "crosserp")
    assert mode is not None
    assert "STRICT_TRANS_TABLES" in mode

    assert (
        mysql_config_error(
            "8.4.7",
            "utf8mb4",
            "ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION",
            "crosserp",
        )
        is None
    )
    assert mysql_config_error("8.4.0", "UTF8MB4", "strict_trans_tables", "crosserp") is None
    assert mysql_config_error("9.0.1", "utf8mb4", "STRICT_TRANS_TABLES", "crosserp") is None
    unsafe = mysql_config_error("8.0.1", "latin1", "", "bad`name")
    assert unsafe is not None
    assert "ALTER DATABASE crosserp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;" in unsafe
    assert "bad`name" not in unsafe


def test_postgres_version_warning_only_below_18() -> None:
    assert postgres_version_warning("18.0") is None
    assert postgres_version_warning("18.1") is None
    warning = postgres_version_warning("16.4")
    assert warning is not None
    assert "18" in warning
    assert "警告" in warning or "不拒绝" in warning


def _mysql_url() -> URL | None:
    raw = os.environ.get("CROSSERP_TEST_DATABASE_URL")
    if not raw:
        return None
    url = make_url(raw)
    if url.get_backend_name() != "mysql":
        return None
    return url


def test_mysql_latin1_database_is_rejected() -> None:
    url = _mysql_url()
    if url is None:
        pytest.skip("没有 MySQL。未设置 CROSSERP_TEST_DATABASE_URL。或当前不是 MySQL")

    admin = make_engine(url.render_as_string(hide_password=False))
    latin = make_engine(url.set(database=_LATIN_DB).render_as_string(hide_password=False))
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {_LATIN_DB}"))
            conn.execute(text(f"CREATE DATABASE {_LATIN_DB} CHARACTER SET latin1"))
        with pytest.raises(DatabaseConfigError, match="utf8mb4") as caught:
            check_server(latin)
        assert "ALTER DATABASE" in str(caught.value)
    finally:
        latin.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {_LATIN_DB}"))
        admin.dispose()
