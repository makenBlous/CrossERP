"""合成样本整套导入。只在调用方提供的库上跑。本地验收用 SQLite。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from crosserp.cli import app, demo_jobs
from crosserp.db.migrate import downgrade_base
from crosserp.db.schema import ImportBatch, Issue, RawRow, Settlement, Store
from crosserp.db.session import session_scope

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[2]
SYNTH = ROOT / "samples" / "synthetic"
_IMPORT_KINDS = frozenset(
    {"SETTLEMENT_UNBALANCED", "UNKNOWN_FEE_TYPE", "DUPLICATE_ROW", "PARSE_ERROR"}
)


def _url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _summary() -> dict[str, object]:
    loaded = json.loads((SYNTH / "expected" / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError("summary.json 不是对象")
    return loaded


def _data_rows(name: str) -> int:
    files = _summary()["files"]
    if not isinstance(files, dict):
        raise AssertionError("summary.json 没有 files")
    entry = files[name]
    if not isinstance(entry, dict) or not isinstance(entry["data_rows"], int):
        raise AssertionError(f"{name} 没有 data_rows")
    return entry["data_rows"]


def _anomalies() -> list[dict[str, object]]:
    loaded = json.loads((SYNTH / "expected" / "anomalies.json").read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise AssertionError("anomalies.json 不是数组")
    rows: list[dict[str, object]] = []
    for item in loaded:
        if not isinstance(item, dict):
            raise AssertionError("anomalies.json 有非对象条目")
        rows.append(item)
    return rows


def _is_import_phase(item: dict[str, object]) -> bool:
    kind = item.get("expected_issue_kind")
    file_name = item.get("file")
    if not isinstance(kind, str) or not isinstance(file_name, str):
        return False
    if kind in _IMPORT_KINDS:
        return True
    return kind == "AMOUNT_MISMATCH" and file_name.startswith("shopify")


def _expected_import_issues() -> set[tuple[str, str, int]]:
    expected: set[tuple[str, str, int]] = set()
    for item in _anomalies():
        if not _is_import_phase(item):
            continue
        kind = item["expected_issue_kind"]
        file_name = item["file"]
        row_nos = item["row_nos"]
        if (
            not isinstance(kind, str)
            or not isinstance(file_name, str)
            or not isinstance(row_nos, list)
        ):
            raise AssertionError("导入阶段异常条目不完整")
        for row_no in row_nos:
            if not isinstance(row_no, int):
                raise AssertionError("行号不是整数")
            expected.add((kind, file_name, row_no))
    return expected


def _actual_issues(engine: Engine) -> set[tuple[str, str, int]]:
    actual: set[tuple[str, str, int]] = set()
    with session_scope(engine) as session:
        for issue in session.scalars(select(Issue)):
            detail = issue.detail_json
            if not isinstance(detail, dict):
                raise AssertionError("issue.detail_json 不是对象")
            source = detail.get("source_file")
            row_no = detail.get("row_no")
            if not isinstance(source, str) or not isinstance(row_no, int):
                raise AssertionError(f"异常缺少文件或行号 {issue.kind} {detail}")
            actual.add((issue.kind, Path(source).name, row_no))
    return actual


def test_demo_import_matches_summary_and_import_anomalies(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    runner = CliRunner()
    jobs = demo_jobs()
    try:
        init = runner.invoke(app, ["init"])
        assert init.exit_code == 0, init.output
        first = runner.invoke(app, ["demo-import"])
        assert first.exit_code == 0, first.output
        assert "已导入过" not in first.output
        with session_scope(engine) as session:
            batches = session.scalars(select(ImportBatch)).all()
            assert len(batches) == len(jobs)
            by_name = {batch.file_name: batch for batch in batches}
            for job in jobs:
                batch = by_name[job.path.name]
                counted = session.scalar(
                    select(func.count()).select_from(RawRow).where(RawRow.batch_id == batch.id)
                )
                assert counted == _data_rows(job.path.name)
                assert counted == batch.row_count
            shopify = session.scalars(
                select(Settlement).where(Settlement.platform == "shopify")
            ).all()
            assert shopify
            assert {item.currency for item in shopify} == {"USD"}
            store = session.get(Store, shopify[0].store_id)
            assert store is not None
            assert store.name == "shopify-main"
        assert _actual_issues(engine) == _expected_import_issues()
        listed = runner.invoke(app, ["issues", "list", "--kind", "SETTLEMENT_UNBALANCED"])
        assert listed.exit_code == 0, listed.output
        assert "共 1 条" in listed.output
        assert listed.output.count("SETTLEMENT_UNBALANCED") == 1
        with session_scope(engine) as session:
            unbalanced = session.scalar(
                select(ImportBatch).where(ImportBatch.file_name == "amazon_us_unbalanced.tsv")
            )
            assert unbalanced is not None
            batch_id = str(unbalanced.id)
        by_batch = runner.invoke(app, ["issues", "list", "--batch", batch_id])
        assert by_batch.exit_code == 0, by_batch.output
        assert "共 1 条" in by_batch.output
        assert "SETTLEMENT_UNBALANCED" in by_batch.output
        before = _actual_issues(engine)
        second = runner.invoke(app, ["demo-import"])
        assert second.exit_code == 0, second.output
        assert second.output.count("跳过") == len(jobs)
        for job in jobs:
            assert f"{job.path.name} 已导入过（" in second.output  # noqa: RUF001
            assert "跳过" in second.output
        assert _actual_issues(engine) == before
        with session_scope(engine) as session:
            assert session.scalar(select(func.count()).select_from(ImportBatch)) == len(jobs)
    finally:
        downgrade_base(url)


def test_unknown_type_lists_options(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CROSSERP_DATABASE_URL", _url(engine))
    path = tmp_path / "notes.txt"
    path.write_text("不是结算文件\n", encoding="utf-8")
    try:
        result = CliRunner().invoke(app, ["import", str(path)])
        assert result.exit_code == 1, result.output
        assert "amazon" in result.output
        assert "shopify" in result.output
        assert "mapped" in result.output
        with session_scope(engine) as session:
            assert session.scalar(select(func.count()).select_from(ImportBatch)) == 0
    finally:
        downgrade_base(_url(engine))


def test_one_file_failure_does_not_stop_others(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    url = _url(engine)
    monkeypatch.setenv("CROSSERP_DATABASE_URL", url)
    missing = tmp_path / "missing.csv"
    orders = SYNTH / "orders.csv"
    mapping = SYNTH / "mappings" / "synthetic_orders.yaml"
    try:
        result = CliRunner().invoke(
            app,
            ["import", str(missing), str(orders), "--type", "mapped", "--mapping", str(mapping)],
        )
        assert result.exit_code == 1, result.output
        assert "无法读取文件" in result.output
        assert "orders.csv" in result.output
        with session_scope(engine) as session:
            names = set(session.scalars(select(ImportBatch.file_name)))
            assert names == {"missing.csv", "orders.csv"}
            missing_batch = session.scalar(
                select(ImportBatch).where(ImportBatch.file_name == "missing.csv")
            )
            assert missing_batch is not None
            assert missing_batch.file_sha256 is None
            assert missing_batch.status == "failed"
            counted = session.scalar(select(func.count()).select_from(RawRow))
            assert counted == _data_rows("orders.csv")
    finally:
        downgrade_base(url)
