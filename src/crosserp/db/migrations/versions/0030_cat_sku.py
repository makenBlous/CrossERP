"""SKU 主档扩展及类目、品牌最小主数据表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_sku"
down_revision: str | Sequence[str] | None = "0030_cat_brand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sku") as batch_op:
        batch_op.alter_column("store_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.add_column(sa.Column("title_en", sa.String(512), nullable=True))
        batch_op.add_column(sa.Column("brand_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("category_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("uom", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("weight_kg", sa.Numeric(18, 6), nullable=True))
        batch_op.add_column(sa.Column("hs_code", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("aliases_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("created_at", UtcDateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", UtcDateTime(), nullable=True))
        batch_op.create_foreign_key(
            "fk_sku_brand_id_brand", "brand", ["brand_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_sku_category_id_category",
            "category",
            ["category_id"],
            ["id"],
        )
        batch_op.create_index("ix_sku_brand_id", ["brand_id"])
        batch_op.create_index("ix_sku_category_id", ["category_id"])

    op.execute(
        sa.text("UPDATE sku SET aliases_json = :empty WHERE aliases_json IS NULL").bindparams(
            empty="[]"
        )
    )
    with op.batch_alter_table("sku") as batch_op:
        batch_op.alter_column("aliases_json", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("sku") as batch_op:
        batch_op.drop_constraint("fk_sku_category_id_category", type_="foreignkey")
        batch_op.drop_constraint("fk_sku_brand_id_brand", type_="foreignkey")
        batch_op.drop_index("ix_sku_category_id")
        batch_op.drop_index("ix_sku_brand_id")
        for name in (
            "updated_at",
            "created_at",
            "aliases_json",
            "hs_code",
            "weight_kg",
            "uom",
            "category_id",
            "brand_id",
            "title_en",
        ):
            batch_op.drop_column(name)
