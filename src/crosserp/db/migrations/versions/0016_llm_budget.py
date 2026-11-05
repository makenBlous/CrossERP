"""T49 AI 预算和告警。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import Money4, UtcDateTime

revision: str = "0016_llm_budget"
down_revision: str | Sequence[str] | None = "0015_llm_observability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_budget",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("limit_amount", Money4(), nullable=True),
        sa.Column("limit_tokens", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("warn_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_budget")),
    )
    op.create_table(
        "llm_alert",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ts", UtcDateTime(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("used_amount", Money4(), nullable=False),
        sa.Column("used_tokens", sa.BigInteger(), nullable=False),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["budget_id"], ["llm_budget.id"], name=op.f("fk_llm_alert_budget_id_llm_budget")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_alert")),
    )


def downgrade() -> None:
    op.drop_table("llm_alert")
    op.drop_table("llm_budget")
