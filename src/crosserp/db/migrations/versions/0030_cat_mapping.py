"""平台 SKU 映射。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_mapping"
down_revision: str | Sequence[str] | None = "0030_cat_listing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sku_mapping",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform_sku", sa.String(128), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("internal_sku", sa.String(128), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["store_id"], ["store.id"], name=op.f("fk_sku_mapping_store_id_store")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sku_mapping")),
    )
    op.create_index("ix_sku_mapping_store_platform", "sku_mapping", ["store_id", "platform_sku"])
    op.create_index("ix_sku_mapping_internal_sku", "sku_mapping", ["internal_sku"])


def downgrade() -> None:
    # Dropping the table also drops its indexes. MySQL needs the FK index.
    op.drop_table("sku_mapping")
