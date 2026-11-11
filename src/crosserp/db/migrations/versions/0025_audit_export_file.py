"""审计导出包落库并关联 FileObject。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_audit_export_file"
down_revision: str | Sequence[str] | None = "0024_audit_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("audit_export", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("actor_type", sa.String(length=16), nullable=False, server_default="human")
        )
        batch_op.add_column(sa.Column("on_behalf_of", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("chain", sa.String(length=32), nullable=False, server_default="audit_log")
        )
        batch_op.add_column(sa.Column("filter_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("file_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="ready")
        )
        batch_op.create_index("ix_audit_export_file_id", ["file_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_audit_export_file_id_file_object", "file_object", ["file_id"], ["id"]
        )
    op.execute(sa.text("UPDATE audit_export SET filter_json = '{}' WHERE filter_json IS NULL"))
    with op.batch_alter_table("audit_export", schema=None) as batch_op:
        batch_op.alter_column(
            "filter_json",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_export", schema=None) as batch_op:
        batch_op.drop_constraint("fk_audit_export_file_id_file_object", type_="foreignkey")
        batch_op.drop_index("ix_audit_export_file_id")
        for name in ("status", "file_id", "filter_json", "chain", "on_behalf_of", "actor_type"):
            batch_op.drop_column(name)
