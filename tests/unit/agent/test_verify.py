from crosserp.agent.tools import Citation
from crosserp.agent.verify import verify_numbers


def test_numbers_must_match_citations() -> None:
    citations = [Citation(table="profit_snapshot", id="1", field="profit", value="123.4500")]
    assert verify_numbers("利润是 123.45[^1]。", citations) == (True, None)
    assert verify_numbers("利润是 999。", citations)[0] is False


def test_derived_difference_is_rejected_and_percent_supported() -> None:
    citations = [Citation(table="profit_snapshot", id="1", field="profit", value="100")]
    assert verify_numbers("下降 20。", citations)[0] is False
    percent = [Citation(table="recon_run", id="1", field="rate", value="95.00%")]
    assert verify_numbers("匹配率 95%[^1]。", percent) == (True, None)


def test_year_is_not_an_amount() -> None:
    assert verify_numbers("2026 年的结果见引用。", []) == (True, None)
