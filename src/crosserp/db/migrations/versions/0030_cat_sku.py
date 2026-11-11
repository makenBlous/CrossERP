"""SKU 主档扩展及类目、品牌最小主数据表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0030_cat_sku"
down_revision: str | Sequence[str] | None = "0024_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sort_no", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["catalog_category.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_category")),
    )
    op.create_index("ix_catalog_category_name", "catalog_category", ["name"])
    op.create_table(
        "catalog_brand",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_brand")),
    )
    op.create_index("ix_catalog_brand_name", "catalog_brand", ["name"])

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
            "fk_sku_brand_id_catalog_brand", "catalog_brand", ["brand_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_sku_category_id_catalog_category",
            "catalog_category",
            ["category_id"],
            ["id"],
        )
        batch_op.create_index("ix_sku_brand_id", ["brand_id"])
        batch_op.create_index("ix_sku_category_id", ["category_id"])


def downgrade() -> None:
    with op.batch_alter_table("sku") as batch_op:
        batch_op.drop_constraint("fk_sku_category_id_catalog_category", type_="foreignkey")
        batch_op.drop_constraint("fk_sku_brand_id_catalog_brand", type_="foreignkey")
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
    op.drop_index("ix_catalog_brand_name", table_name="catalog_brand")
    op.drop_table("catalog_brand")
    op.drop_index("ix_catalog_category_name", table_name="catalog_category")
    op.drop_table("catalog_category")
