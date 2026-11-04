"""审批状态转移表的穷举和随机检查。"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from crosserp.approval.state import ApprovalState, IllegalTransition, allowed_targets, transition


def test_every_state_pair_matches_transition_table() -> None:
    expected = {
        ApprovalState.DRAFT: {ApprovalState.PENDING},
        ApprovalState.PENDING: {ApprovalState.APPROVED, ApprovalState.REJECTED},
        ApprovalState.APPROVED: {ApprovalState.EXPORTED, ApprovalState.PENDING},
        ApprovalState.REJECTED: {ApprovalState.DRAFT},
        ApprovalState.EXPORTED: set(),
    }
    for current in ApprovalState:
        assert allowed_targets(current) == frozenset(expected[current])
        for target in ApprovalState:
            if target in expected[current]:
                assert transition(current, target) == target
            else:
                with pytest.raises(IllegalTransition):
                    transition(current, target)


@given(st.lists(st.sampled_from(list(ApprovalState)), min_size=1, max_size=100))
def test_random_operations_never_leave_known_state(targets: list[ApprovalState]) -> None:
    current = ApprovalState.DRAFT
    for target in targets:
        if target in allowed_targets(current):
            current = transition(current, target)
        assert current in set(ApprovalState)
