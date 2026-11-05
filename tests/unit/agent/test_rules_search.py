from pathlib import Path

from crosserp.agent.rules_search import search_rules_doc


def test_rules_search_returns_file_and_line(tmp_path: Path) -> None:
    (tmp_path / "rules.md").write_text("# 退款\n退款不得改写收入\n", encoding="utf-8")
    hits = search_rules_doc("退款 收入", root=tmp_path)
    assert hits and hits[0].file == "rules.md" and hits[0].line_start == 2
