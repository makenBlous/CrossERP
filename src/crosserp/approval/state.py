"""审批状态和值域转移。"""

from __future__ import annotations

from enum import StrEnum

from crosserp.core.errors import CrossErpError


class ApprovalState(StrEnum):
    """审批单生命周期。"""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"


class IllegalTransition(CrossErpError):
    """审批状态不能执行指定的转移。"""

    def __init__(self, current: ApprovalState | str, target: ApprovalState | str) -> None:
        self.current = str(current)
        self.target = str(target)
        super().__init__(f"审批状态不能从 {self.current} 转为 {self.target}")


class ConcurrentModification(CrossErpError):
    """审批单已被另一个事务修改。"""

    def __init__(self, approval_id: object) -> None:
        self.approval_id = str(approval_id)
        super().__init__(f"审批单 {self.approval_id} 已被其他操作修改，请重新读取后再试")  # noqa: RUF001


_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.DRAFT: frozenset({ApprovalState.PENDING}),
    ApprovalState.PENDING: frozenset({ApprovalState.APPROVED, ApprovalState.REJECTED}),
    ApprovalState.APPROVED: frozenset({ApprovalState.EXPORTED, ApprovalState.PENDING}),
    ApprovalState.REJECTED: frozenset({ApprovalState.DRAFT}),
    ApprovalState.EXPORTED: frozenset(),
}


def coerce_state(value: ApprovalState | str) -> ApprovalState:
    """把数据库里的字符串转为受控状态。"""
    try:
        return value if isinstance(value, ApprovalState) else ApprovalState(value)
    except ValueError as exc:
        raise ValueError(f"不认识的审批状态 {value!r}") from exc


def transition(current: ApprovalState | str, target: ApprovalState | str) -> ApprovalState:
    """校验并返回目标状态。"""
    source = coerce_state(current)
    destination = coerce_state(target)
    if destination not in _TRANSITIONS[source]:
        raise IllegalTransition(source, destination)
    return destination


def allowed_targets(current: ApprovalState | str) -> frozenset[ApprovalState]:
    """返回状态允许到达的目标，供测试和界面展示。"""  # noqa: RUF002
    return _TRANSITIONS[coerce_state(current)]
