"""对账结果基础性质。"""

from hypothesis import given
from hypothesis import strategies as st


@given(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=30))
def test_matched_plus_unmatched_equals_total(values: list[int]) -> None:
    matched = sum(value % 2 == 0 for value in values)
    unmatched = len(values) - matched
    assert matched + unmatched == len(values)
