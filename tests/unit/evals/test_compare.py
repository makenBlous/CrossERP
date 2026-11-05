import json
from pathlib import Path

from crosserp.evals.run import compare


def test_compare_detects_regression(tmp_path: Path) -> None:
    baseline = {"passed": 2, "results": [{"id": "a", "passed": True}, {"id": "b", "passed": True}]}
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    ok, problems = compare(
        {"passed": 1, "results": [{"id": "a", "passed": True}, {"id": "b", "passed": False}]}, path
    )
    assert not ok and problems


def test_compare_accepts_equal_or_higher_score(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps({"passed": 1, "results": [{"id": "a", "passed": True}]}),
        encoding="utf-8",
    )
    ok, problems = compare(
        {"passed": 2, "results": [{"id": "a", "passed": True}, {"id": "b", "passed": True}]},
        path,
    )
    assert ok and problems == []


def test_compare_detects_missing_previously_passing_question(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps({"passed": 1, "results": [{"id": "a", "passed": True}]}),
        encoding="utf-8",
    )
    ok, problems = compare({"passed": 1, "results": []}, path)
    assert not ok
    assert "题目由通过变失败: a" in problems
