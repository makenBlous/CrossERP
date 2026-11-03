"""Add detailed, replayable profit snapshot columns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import FxRate, Money4

revision: str = "0007_profit_snapshot_cols"
down_revision: str | Sequence[str] | None = "0006_fee_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profit_snapshot", schema=None) as batch_op:
        batch_op.alter_column("cogs", existing_type=Money4(), nullable=True)
        batch_op.alter_column("freight", existing_type=Money4(), nullable=True)
        batch_op.alter_column("profit", existing_type=Money4(), nullable=True)
        batch_op.add_column(sa.Column("qty_sold", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("qty_refunded", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("qty_net", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("promotion", Money4(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("fx_rate", FxRate(), nullable=True))
        batch_op.add_column(sa.Column("profit_cny", Money4(), nullable=True))
        batch_op.add_column(
            sa.Column("ads_included", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ok")
        )
        batch_op.add_column(sa.Column("recon_run_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_profit_snapshot_recon_run_id_recon_run",
            "recon_run",
            ["recon_run_id"],
            ["id"],
        )
        batch_op.create_index("ix_profit_snapshot_recon_run_id", ["recon_run_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("profit_snapshot", schema=None) as batch_op:
        batch_op.drop_constraint("fk_profit_snapshot_recon_run_id_recon_run", type_="foreignkey")
        batch_op.drop_index("ix_profit_snapshot_recon_run_id")
        batch_op.drop_column("recon_run_id")
        batch_op.drop_column("status")
        batch_op.drop_column("ads_included")
        batch_op.drop_column("profit_cny")
        batch_op.drop_column("fx_rate")
        batch_op.drop_column("promotion")
        batch_op.drop_column("qty_net")
        batch_op.drop_column("qty_refunded")
        batch_op.drop_column("qty_sold")
        batch_op.alter_column("profit", existing_type=Money4(), nullable=False)
        batch_op.alter_column("freight", existing_type=Money4(), nullable=False)
        batch_op.alter_column("cogs", existing_type=Money4(), nullable=False)
