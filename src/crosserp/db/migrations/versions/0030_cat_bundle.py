"""组合装实体。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_bundle"
down_revision: str | Sequence[str] | None = "0024_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bundle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bundle_sku", sa.String(128), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bundle")),
        sa.UniqueConstraint("bundle_sku", name="uq_bundle_bundle_sku"),
    )


def downgrade() -> None:
    op.drop_table("bundle")
