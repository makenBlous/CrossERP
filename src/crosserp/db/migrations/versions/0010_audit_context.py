"""补充审计显示名并保留旧哈希算法版本。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_audit_context"
down_revision: str | Sequence[str] | None = "0009_export_artifact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.add_column(sa.Column("actor_name", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("hash_version", sa.Integer(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_column("hash_version")
        batch_op.drop_column("actor_name")
