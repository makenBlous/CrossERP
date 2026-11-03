"""Create fee reference values used by reconciliation warnings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import Money4, UtcDateTime

revision: str = "0006_fee_reference"
down_revision: str | Sequence[str] | None = "0005_recon_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fee_reference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("internal_sku", sa.String(length=64), nullable=False),
        sa.Column("fee_category", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expected_per_unit", Money4(), nullable=False),
        sa.Column("valid_from", UtcDateTime(), nullable=False),
        sa.Column("valid_to", UtcDateTime(), nullable=True),
        sa.Column("source_batch_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["store_id"], ["store.id"], name=op.f("fk_fee_reference_store_id_store")
        ),
        sa.ForeignKeyConstraint(
            ["source_batch_id"],
            ["import_batch.id"],
            name=op.f("fk_fee_reference_source_batch_id_import_batch"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fee_reference")),
    )
    with op.batch_alter_table("fee_reference", schema=None) as batch_op:
        batch_op.create_index("ix_fee_reference_internal_sku", ["internal_sku"], unique=False)
        batch_op.create_index("ix_fee_reference_source_batch_id", ["source_batch_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("fee_reference", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_fee_reference_source_batch_id_import_batch", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_fee_reference_store_id_store", type_="foreignkey")
        batch_op.drop_index("ix_fee_reference_source_batch_id")
        batch_op.drop_index("ix_fee_reference_internal_sku")
    op.drop_table("fee_reference")
