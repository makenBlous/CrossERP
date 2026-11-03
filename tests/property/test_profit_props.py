"""利润输入哈希和 SKU 汇总性质。"""

from hypothesis import given
from hypothesis import strategies as st

from crosserp.profit.inputs import inputs_hash


@given(st.lists(st.uuids(), min_size=1, max_size=20))
def test_inputs_hash_is_order_independent(values: list[object]) -> None:
    assert inputs_hash(values) == inputs_hash(reversed(values))


def test_inputs_hash_changes_when_an_input_changes() -> None:
    assert inputs_hash(["a", "b"]) != inputs_hash(["a", "c"])
