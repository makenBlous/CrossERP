"""导入批次成功去重、失败原因和重试关联。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_import_batch_fields"
down_revision: str | Sequence[str] | None = "0003_import_retry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add retry metadata and a unique key only for successful batches."""
    with op.batch_alter_table("import_batch", schema=None) as batch_op:
        batch_op.add_column(sa.Column("done_sha256", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("retry_of_batch_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("failure_code", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("failure_reason", sa.String(length=1000), nullable=True))
        batch_op.create_foreign_key(
            "fk_import_batch_retry_of_batch_id_import_batch",
            "import_batch",
            ["retry_of_batch_id"],
            ["id"],
        )
        batch_op.create_index("ix_import_batch_file_sha256", ["file_sha256"], unique=False)
        batch_op.create_unique_constraint("uq_import_batch_done_sha256", ["done_sha256"])

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE import_batch SET done_sha256 = file_sha256 "
            "WHERE status = 'done' AND file_sha256 IS NOT NULL"
        )
    )


def downgrade() -> None:
    """Remove the metadata introduced by this migration."""
    connection = op.get_bind()
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("import_batch", schema=None) as batch_op:
            batch_op.drop_constraint("uq_import_batch_done_sha256", type_="unique")
            batch_op.drop_index("ix_import_batch_file_sha256")
            batch_op.drop_constraint(
                "fk_import_batch_retry_of_batch_id_import_batch", type_="foreignkey"
            )
            batch_op.drop_column("failure_reason")
            batch_op.drop_column("failure_code")
            batch_op.drop_column("retry_of_batch_id")
            batch_op.drop_column("done_sha256")
    finally:
        if sqlite:
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))
