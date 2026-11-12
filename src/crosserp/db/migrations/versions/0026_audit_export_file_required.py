"""审计导出必须关联已落库的 FileObject。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_audit_export_file_required"
down_revision: str | Sequence[str] | None = "0025_audit_export_file"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("audit_export", schema=None) as batch_op:
        batch_op.alter_column(
            "file_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_export", schema=None) as batch_op:
        batch_op.alter_column(
            "file_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
