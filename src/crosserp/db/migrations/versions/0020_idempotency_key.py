"""P0 公共 API 的 24 小时幂等键。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0020_idempotency_key"
down_revision: str | Sequence[str] | None = "0019_llm_text_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("response_headers", sa.JSON(), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("expires_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_key")),
    )
    op.create_index("ix_idempotency_key_key", "idempotency_key", ["key"], unique=True)
    op.create_index(
        "ix_idempotency_key_expires_at", "idempotency_key", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_key_expires_at", table_name="idempotency_key")
    op.drop_index("ix_idempotency_key_key", table_name="idempotency_key")
    op.drop_table("idempotency_key")
