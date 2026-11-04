"""W4 审批后的导出产物记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0009_export_artifact"
down_revision: str | Sequence[str] | None = "0008_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_artifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("ext_ref", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["approval_id"], ["approval.id"], name=op.f("fk_export_artifact_approval_id_approval")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_artifact")),
    )
    with op.batch_alter_table("export_artifact", schema=None) as batch_op:
        batch_op.create_index("ix_export_artifact_approval_id", ["approval_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("export_artifact", schema=None) as batch_op:
        batch_op.drop_constraint("fk_export_artifact_approval_id_approval", type_="foreignkey")
        batch_op.drop_index("ix_export_artifact_approval_id")
    op.drop_table("export_artifact")
