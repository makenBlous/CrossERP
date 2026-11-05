from crosserp.evals.scorers import score


def test_scorer_accepts_facts_and_citations() -> None:
    question = {
        "id": "q1",
        "expected_facts": ["123.45"],
        "must_cite": ["profit_snapshot"],
        "must_refuse": False,
    }
    assert score(question, "123.45", ["profit_snapshot row"])["passed"]


def test_scorer_rejects_wrong_fact_and_missing_refusal() -> None:
    question = {"id": "q2", "expected_facts": ["数据不足"], "must_cite": [], "must_refuse": True}
    assert score(question, "利润是 10", [])["passed"] is False
