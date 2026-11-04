"""审批状态机和审批服务。"""

from crosserp.approval.state import ApprovalState, ConcurrentModification, IllegalTransition

__all__ = ["ApprovalState", "ConcurrentModification", "IllegalTransition"]
