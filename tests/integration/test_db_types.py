"""Money4 / FxRate / UtcDateTime 在真实数据库上的往返。"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, select, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import IntegrityError, StatementError
from typer.testing import CliRunner

from crosserp.cli import app
from crosserp.core.errors import DatabaseConfigError, PrecisionError
from crosserp.db.dialects import check_server
from crosserp.db.session import get_database_url, make_engine, session_scope
from crosserp.db.types import FxRate, Money4, UtcDateTime

pytestmark = pytest.mark.db

_BEIJING = timezone(timedelta(hours=8))


class _Dialect:
    def __init__(self, name: str) -> None:
        self.name = name


@contextmanager
def raises_from_bind(expected: type[Exception], match: str | None = None) -> Iterator[None]:
    """SQLAlchemy 会把类型处理器的异常包成 StatementError。核对原始异常。"""
    with pytest.raises(StatementError, match=match) as caught:
        yield
    assert isinstance(caught.value.__cause__, expected)


def _name(prefix: str) -> str:
    return f"t04_{prefix}_{uuid.uuid4().hex[:8]}"


def _money_table() -> tuple[MetaData, Table]:
    metadata = MetaData()
    table = Table(
        _name("money"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Money4(), nullable=False),
    )
    return metadata, table


def _insert_amount(engine: Engine, value: Decimal) -> tuple[MetaData, Table]:
    metadata, table = _money_table()
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(table.insert().values(id=1, amount=value))
    return metadata, table


@pytest.mark.parametrize(
    "value",
    [
        Decimal("12345678.1234"),
        Decimal("-0.0001"),
        Decimal("0"),
        Decimal("99999999999999.9999"),
        Decimal("-922337203685477.5807"),
    ],
)
def test_money4_roundtrip(engine: Engine, value: Decimal) -> None:
    metadata, table = _insert_amount(engine, value)
    try:
        with engine.connect() as conn:
            loaded = conn.execute(select(table.c.amount)).scalar_one()
            raw = conn.exec_driver_sql(f"SELECT amount FROM {table.name}").scalar_one()
        assert isinstance(loaded, Decimal)
        assert loaded == value
        assert str(loaded) == f"{value:.4f}"
        if engine.dialect.name == "sqlite":
            assert isinstance(raw, int)
            assert raw == int(value * 10000)
        else:
            assert isinstance(raw, Decimal)
            assert raw == value
    finally:
        metadata.drop_all(engine)


def test_money4_bind_rejects_bad_values() -> None:
    money = Money4()
    sqlite = _Dialect("sqlite")
    mysql = _Dialect("mysql")
    with pytest.raises(PrecisionError):
        money.process_bind_param(Decimal("1.23456"), sqlite)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="float"):
        money.process_bind_param(1.5, sqlite)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        money.process_bind_param(1, sqlite)  # type: ignore[arg-type]
    with pytest.raises(PrecisionError, match="DECIMAL"):
        money.process_bind_param(Decimal("1000000000000000.0000"), mysql)  # type: ignore[arg-type]
    with pytest.raises(PrecisionError, match=r"922337203685477\.5807"):
        money.process_bind_param(Decimal("922337203685477.5808"), sqlite)  # type: ignore[arg-type]


def test_money4_rejects_extra_places(engine: Engine) -> None:
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        with raises_from_bind(PrecisionError), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, amount=Decimal("1.23456")))
    finally:
        metadata.drop_all(engine)


def test_money4_rejects_float(engine: Engine) -> None:
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        with raises_from_bind(TypeError, match="float"), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, amount=1.5))
    finally:
        metadata.drop_all(engine)


def test_money4_rejects_int(engine: Engine) -> None:
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        with raises_from_bind(TypeError), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, amount=1))
    finally:
        metadata.drop_all(engine)


def test_money4_rejects_decimal_19_4_overflow(engine: Engine) -> None:
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        with raises_from_bind(PrecisionError, match="DECIMAL"), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, amount=Decimal("1000000000000000.0000")))
    finally:
        metadata.drop_all(engine)


def test_sqlite_money4_int64_limit(engine: Engine) -> None:
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        over = Decimal("922337203685477.5808")
        if engine.dialect.name == "sqlite":
            with (
                raises_from_bind(PrecisionError, match=r"922337203685477\.5807"),
                engine.begin() as conn,
            ):
                conn.execute(table.insert().values(id=1, amount=over))
            with raises_from_bind(PrecisionError), engine.begin() as conn:
                conn.execute(table.insert().values(id=2, amount=Decimal("-922337203685477.5808")))
        else:
            with engine.begin() as conn:
                conn.execute(table.insert().values(id=1, amount=over))
                loaded = conn.execute(select(table.c.amount)).scalar_one()
            assert loaded == over
            assert str(loaded) == f"{over:.4f}"
    finally:
        metadata.drop_all(engine)


def test_sqlite_money4_max_fits(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        pytest.skip("只断言 SQLite 万分位上限本身可以写入")
    value = Decimal("922337203685477.5807")
    metadata, table = _insert_amount(engine, value)
    try:
        with engine.connect() as conn:
            loaded = conn.execute(select(table.c.amount)).scalar_one()
            raw = conn.exec_driver_sql(f"SELECT amount FROM {table.name}").scalar_one()
        assert loaded == value
        assert str(loaded) == "922337203685477.5807"
        assert raw == 9223372036854775807
    finally:
        metadata.drop_all(engine)


def test_decimal_19_4_max_on_server_decimal(engine: Engine) -> None:
    value = Decimal("999999999999999.9999")
    metadata, table = _money_table()
    metadata.create_all(engine)
    try:
        if engine.dialect.name == "sqlite":
            with raises_from_bind(PrecisionError), engine.begin() as conn:
                conn.execute(table.insert().values(id=1, amount=value))
        else:
            with engine.begin() as conn:
                conn.execute(table.insert().values(id=1, amount=value))
                loaded = conn.execute(select(table.c.amount)).scalar_one()
            assert loaded == value
            assert str(loaded) == "999999999999999.9999"
    finally:
        metadata.drop_all(engine)


def test_fx_rate_roundtrip(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("fx"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("rate", FxRate(), nullable=False),
    )
    metadata.create_all(engine)
    value = Decimal("7.12345678")
    try:
        with engine.begin() as conn:
            conn.execute(table.insert().values(id=1, rate=value))
        with engine.connect() as conn:
            loaded = conn.execute(select(table.c.rate)).scalar_one()
            raw = conn.exec_driver_sql(f"SELECT rate FROM {table.name}").scalar_one()
        assert loaded == value
        assert str(loaded) == "7.12345678"
        if engine.dialect.name == "sqlite":
            assert raw == "7.12345678"
    finally:
        metadata.drop_all(engine)


def test_fx_rate_rejects_extra_places(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("fxbad"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("rate", FxRate(), nullable=False),
    )
    metadata.create_all(engine)
    try:
        with raises_from_bind(PrecisionError), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, rate=Decimal("1.123456789")))
    finally:
        metadata.drop_all(engine)


def test_fx_rate_rejects_float(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("fxfloat"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("rate", FxRate(), nullable=False),
    )
    metadata.create_all(engine)
    try:
        with raises_from_bind(TypeError, match="float"), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, rate=1.5))
    finally:
        metadata.drop_all(engine)


def test_utc_datetime_converts_beijing_to_utc(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("ts"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("happened_at", UtcDateTime(), nullable=False),
    )
    metadata.create_all(engine)
    written = datetime(2026, 11, 9, 8, 0, tzinfo=_BEIJING)
    try:
        with engine.begin() as conn:
            conn.execute(table.insert().values(id=1, happened_at=written))
        with engine.connect() as conn:
            loaded = conn.execute(select(table.c.happened_at)).scalar_one()
        assert loaded == datetime(2026, 11, 9, 0, 0, tzinfo=UTC)
        assert loaded.tzinfo is UTC
    finally:
        metadata.drop_all(engine)


def test_utc_datetime_rejects_naive(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("naive"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("happened_at", UtcDateTime(), nullable=False),
    )
    metadata.create_all(engine)
    try:
        with raises_from_bind(ValueError), engine.begin() as conn:
            conn.execute(table.insert().values(id=1, happened_at=datetime(2026, 11, 9, 8, 0)))
    finally:
        metadata.drop_all(engine)


def test_unicode_title_roundtrip(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("title"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False),
    )
    metadata.create_all(engine)
    title = "保温杯 🍵 黑色"
    try:
        with engine.begin() as conn:
            conn.execute(table.insert().values(id=1, title=title))
        with engine.connect() as conn:
            loaded = conn.execute(select(table.c.title)).scalar_one()
        assert loaded == title
    finally:
        metadata.drop_all(engine)


def test_null_optional_columns(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("nulls"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Money4(), nullable=False),
        Column("rate", FxRate(), nullable=True),
        Column("happened_at", UtcDateTime(), nullable=True),
        Column("title", String(255), nullable=True),
    )
    metadata.create_all(engine)
    try:
        with engine.begin() as conn:
            conn.execute(table.insert().values(id=1, amount=Decimal("0")))
            row = conn.execute(select(table)).one()
        assert row.amount == Decimal("0")
        assert str(row.amount) == "0.0000"
        assert row.rate is None
        assert row.happened_at is None
        assert row.title is None
    finally:
        metadata.drop_all(engine)


def test_type_cache_ok() -> None:
    assert Money4.cache_ok is True
    assert FxRate.cache_ok is True
    assert UtcDateTime.cache_ok is True


def test_foreign_keys_enforced(engine: Engine) -> None:
    metadata = MetaData()
    parent_name = _name("parent")
    child_name = _name("child")
    Table(parent_name, metadata, Column("id", Integer, primary_key=True))
    child = Table(
        child_name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey(f"{parent_name}.id"), nullable=False),
    )
    metadata.create_all(engine)
    try:
        if engine.dialect.name == "sqlite":
            with engine.connect() as conn:
                assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(child.insert().values(id=1, parent_id=999))
    finally:
        metadata.drop_all(engine)


def test_session_scope_commits_and_rolls_back(engine: Engine) -> None:
    metadata = MetaData()
    table = Table(
        _name("scope"),
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(32), nullable=False),
    )
    metadata.create_all(engine)
    try:
        with session_scope(engine) as session:
            session.execute(table.insert().values(id=1, name="ok"))
        with engine.connect() as conn:
            assert conn.execute(select(table.c.name)).scalar_one() == "ok"
        with pytest.raises(RuntimeError), session_scope(engine) as session:
            session.execute(table.insert().values(id=2, name="bad"))
            raise RuntimeError("boom")
        with engine.connect() as conn:
            assert conn.execute(select(table.c.name)).scalars().all() == ["ok"]
    finally:
        metadata.drop_all(engine)


def test_get_database_url_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CROSSERP_DATABASE_URL", "sqlite:///C:/tmp/custom.db")
    assert get_database_url() == "sqlite:///C:/tmp/custom.db"


def test_default_sqlite_url_creates_directory_and_connects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CROSSERP_DATABASE_URL", raising=False)
    monkeypatch.setattr("crosserp.db.session.Path.home", lambda: tmp_path)
    url = get_database_url()
    assert url.startswith("sqlite:///")
    assert "data.db" in url
    assert "\\" not in url
    assert (tmp_path / ".crosserp").is_dir()
    database = make_engine(url)
    try:
        with database.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        database.dispose()
    assert (tmp_path / ".crosserp" / "data.db").is_file()


def test_mysql_url_requires_utf8mb4_charset() -> None:
    with pytest.raises(DatabaseConfigError, match="utf8mb4") as missing:
        make_engine("mysql+pymysql://root:supersecret@127.0.0.1:3306/crosserp")
    assert "supersecret" not in str(missing.value)
    with pytest.raises(DatabaseConfigError, match="utf8mb4"):
        make_engine("mysql+pymysql://root:dev@127.0.0.1:3306/crosserp?charset=utf8")


def test_check_server_on_fixture_engine(engine: Engine) -> None:
    status = check_server(engine)
    assert status.dialect == engine.dialect.name
    assert status.version
    if engine.dialect.name == "mysql":
        assert status.charset is not None
        assert status.charset.casefold() == "utf8mb4"
        assert status.strict_trans_tables is True


def test_cli_db_check_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = URL.create(
        drivername="sqlite", database=str((tmp_path / "cli.db").resolve())
    ).render_as_string(hide_password=False)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    result = CliRunner().invoke(app, ["db", "check"])
    assert result.exit_code == 0, result.output
    assert "SQLite" in result.output
    assert "自检: OK" in result.output


def test_cli_db_check_rejects_mysql_without_charset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CROSSERP_DATABASE_URL",
        "mysql+pymysql://root:supersecret@127.0.0.1:3306/crosserp",
    )
    result = CliRunner().invoke(app, ["db", "check"])
    assert result.exit_code == 1
    assert "utf8mb4" in result.output
    assert "supersecret" not in result.output


def test_cli_version_still_works() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.0.1"
