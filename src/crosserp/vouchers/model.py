"""凭证领域模型。只保存 Decimal, 不使用 float。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class VoucherLineDraft:
    """一条只能借或贷一边的凭证分录。"""

    line_no: int
    account_key: str
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    summary: str
    source_ref: str

    def __post_init__(self) -> None:
        if self.debit < 0 or self.credit < 0:
            raise ValueError("凭证借方和贷方不能为负数")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("一条凭证分录不能同时有借方和贷方")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("凭证分录不能借贷同时为零")


@dataclass(frozen=True)
class VoucherDraft:
    """借贷平衡的凭证草稿。"""

    id: UUID | None
    store_id: UUID
    period: str
    source_type: str
    source_id: str
    currency: str
    inputs_hash: str
    accounts_hash: str
    created_by: str
    lines: tuple[VoucherLineDraft, ...] = field(default_factory=tuple)

    @property
    def total_debit(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0"))

    @property
    def total_credit(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0"))

    def validate_balance(self) -> None:
        if self.total_debit != self.total_credit:
            raise ValueError(f"凭证借贷不平: 借方 {self.total_debit} != 贷方 {self.total_credit}")
        if not self.lines:
            raise ValueError("凭证至少需要一条分录")
