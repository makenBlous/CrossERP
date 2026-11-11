"""品牌主数据。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_brand"
down_revision: str | Sequence[str] | None = "0024_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brand",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brand")),
    )
    op.create_index("ix_brand_name", "brand", ["name"])


def downgrade() -> None:
    op.drop_index("ix_brand_name", table_name="brand")
    op.drop_table("brand")
