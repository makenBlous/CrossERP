"""SKU 成本期间 API 字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_cost"
down_revision: str | Sequence[str] | None = "0030_cat_bundle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sku_cost", schema=None) as batch_op:
        batch_op.add_column(sa.Column("period", sa.String(7), nullable=True))
        batch_op.add_column(
            sa.Column("source", sa.String(16), server_default="purchase", nullable=False)
        )
        batch_op.add_column(
            sa.Column("status", sa.String(16), server_default="effective", nullable=False)
        )
        batch_op.add_column(sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(
            sa.Column(
                "created_at",
                UtcDateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                UtcDateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("provenance_json", sa.JSON(), nullable=True))
        batch_op.create_index("ix_sku_cost_period", ["internal_sku", "period"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sku_cost", schema=None) as batch_op:
        batch_op.drop_index("ix_sku_cost_period")
        batch_op.drop_column("provenance_json")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("version")
        batch_op.drop_column("status")
        batch_op.drop_column("source")
        batch_op.drop_column("period")
