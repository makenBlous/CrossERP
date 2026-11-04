"""W4 审计检查点和离线导出索引。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0011_audit_export"
down_revision: str | Sequence[str] | None = "0010_audit_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_checkpoint",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chain", sa.String(length=32), nullable=False),
        sa.Column("upto_id", sa.Uuid(), nullable=True),
        sa.Column("upto_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_checkpoint")),
    )
    with op.batch_alter_table("audit_checkpoint", schema=None) as batch_op:
        batch_op.create_index(
            "ix_audit_checkpoint_chain_created_at", ["chain", "created_at"], unique=False
        )
    op.create_table(
        "audit_export",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("from_ts", UtcDateTime(), nullable=False),
        sa.Column("to_ts", UtcDateTime(), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("first_hash", sa.String(length=64), nullable=True),
        sa.Column("last_hash", sa.String(length=64), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_export")),
    )


def downgrade() -> None:
    op.drop_table("audit_export")
    with op.batch_alter_table("audit_checkpoint", schema=None) as batch_op:
        batch_op.drop_index("ix_audit_checkpoint_chain_created_at")
    op.drop_table("audit_checkpoint")
