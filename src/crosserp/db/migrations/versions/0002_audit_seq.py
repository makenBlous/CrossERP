"""audit_log 增加单调序号 seq。

人工检查过。seq 由应用分配。不用 Identity。没有方言专属类型。

Revision ID: 0002_audit_seq
Revises: 0001_initial
Create Date: 2026-11-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_audit_seq"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.add_column(sa.Column("seq", sa.Integer(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM audit_log ORDER BY ts, id")).fetchall()
    for index, row in enumerate(rows, start=1):
        connection.execute(
            sa.text("UPDATE audit_log SET seq = :seq WHERE id = :id"),
            {"seq": index, "id": row[0]},
        )

    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.alter_column(
            "seq",
            existing_type=sa.Integer(),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.create_unique_constraint("uq_audit_log_seq", ["seq"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_column("seq")
