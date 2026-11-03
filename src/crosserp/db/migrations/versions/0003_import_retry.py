"""失败批次允许重导。打不开的文件 sha256 留空。

人工检查过。去掉 file_sha256 唯一约束。允许该列为空。
没有方言专属类型。成功批次是否重复由应用判断。

Revision ID: 0003_import_retry
Revises: 0002_audit_seq
Create Date: 2026-11-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_import_retry"
down_revision: str | Sequence[str] | None = "0002_audit_seq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("import_batch", schema=None) as batch_op:
        batch_op.drop_constraint("uq_import_batch_file_sha256", type_="unique")
        batch_op.alter_column(
            "file_sha256",
            existing_type=sa.String(length=64),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
    rows = connection.execute(
        sa.text("SELECT id, file_sha256 FROM import_batch ORDER BY imported_at, id")
    ).fetchall()
    seen: set[str] = set()
    for index, row in enumerate(rows):
        sha = row[1]
        if isinstance(sha, str) and sha not in seen:
            seen.add(sha)
            continue
        placeholder = f"downgrade-{index:04d}".ljust(64, "0")[:64]
        connection.execute(
            sa.text("UPDATE import_batch SET file_sha256 = :sha WHERE id = :id"),
            {"sha": placeholder, "id": row[0]},
        )
        seen.add(placeholder)
    with op.batch_alter_table("import_batch", schema=None) as batch_op:
        batch_op.alter_column(
            "file_sha256",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_unique_constraint("uq_import_batch_file_sha256", ["file_sha256"])
    if sqlite:
        connection.execute(sa.text("PRAGMA foreign_keys=ON"))
