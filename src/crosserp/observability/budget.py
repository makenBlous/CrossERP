"""AI 预算检查。金额优先, 未配价格时使用 token 上限。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import LlmAlert, LlmBudget, LlmCall


def check(session: Session, *, user_id: UUID | None = None, now: datetime | None = None) -> str:
    moment = now or datetime.now(UTC)
    period = moment.strftime("%Y-%m")
    budget = session.scalar(
        select(LlmBudget)
        .where(LlmBudget.period == period, LlmBudget.scope == "global")
        .order_by(LlmBudget.created_at.desc())
    )
    if budget is None:
        return "ok"
    calls = list(
        session.scalars(
            select(LlmCall).where(LlmCall.ts >= datetime(moment.year, moment.month, 1, tzinfo=UTC))
        )
    )
    amount = sum((row.cost_estimate or Decimal(0) for row in calls), Decimal(0))
    tokens = sum(row.input_tokens + row.output_tokens for row in calls)
    used = (
        amount / budget.limit_amount * 100
        if budget.limit_amount
        else (Decimal(tokens) / Decimal(budget.limit_tokens or 1) * 100)
    )
    kind = "block" if used >= 100 else "warn" if used >= budget.warn_percent else "ok"
    if (
        kind in {"warn", "block"}
        and session.scalar(
            select(LlmAlert.id).where(LlmAlert.budget_id == budget.id, LlmAlert.kind == kind)
        )
        is None
    ):
        session.add(
            LlmAlert(
                id=uuid4(),
                ts=moment,
                budget_id=budget.id,
                kind=kind,
                used_amount=amount,
                used_tokens=tokens,
                acknowledged_by=None,
                acknowledged_at=None,
            )
        )
    return kind
