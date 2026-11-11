"""平台 Listing。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import Money4, UtcDateTime

revision: str = "0030_cat_listing"
down_revision: str | Sequence[str] | None = "0024_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listing",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("platform_sku", sa.String(128), nullable=False),
        sa.Column("asin", sa.String(64), nullable=True),
        sa.Column("price", Money4(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"], name="fk_listing_store_id_store"),
        sa.PrimaryKeyConstraint("id", name="pk_listing"),
        sa.UniqueConstraint("store_id", "platform_sku", name="uq_listing_store_platform_sku"),
    )
    op.create_index("ix_listing_store_id", "listing", ["store_id"])
    op.create_index("ix_listing_status", "listing", ["status"])


def downgrade() -> None:
    op.drop_index("ix_listing_status", table_name="listing")
    op.drop_index("ix_listing_store_id", table_name="listing")
    op.drop_table("listing")
