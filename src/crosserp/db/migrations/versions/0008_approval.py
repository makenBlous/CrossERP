"""W4 审批状态机。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0008_approval"
down_revision: str | Sequence[str] | None = "0007_profit_snapshot_cols"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create approval records and their one-time token index."""
    op.create_table(
        "approval",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("requested_at", UtcDateTime(), nullable=False),
        sa.Column("approver", sa.String(length=64), nullable=True),
        sa.Column("decided_at", UtcDateTime(), nullable=True),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("used_at", UtcDateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval")),
        sa.UniqueConstraint("token_hash", name="uq_approval_token_hash"),
    )
    op.create_index(
        "ix_approval_target_type_target_id",
        "approval",
        ["target_type", "target_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the approval table."""
    op.drop_index("ix_approval_target_type_target_id", table_name="approval")
    op.drop_table("approval")
