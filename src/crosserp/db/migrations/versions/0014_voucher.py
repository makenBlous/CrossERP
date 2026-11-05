"""T39 凭证草稿和分录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import Money4, UtcDateTime

revision: str = "0014_voucher"
down_revision: str | Sequence[str] | None = "0013_security_event"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "voucher",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_debit", Money4(), nullable=False),
        sa.Column("total_credit", Money4(), nullable=False),
        sa.Column("inputs_hash", sa.String(length=64), nullable=False),
        sa.Column("accounts_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.CheckConstraint(
            "total_debit >= 0 AND total_credit >= 0", name="voucher_totals_nonnegative"
        ),
        sa.ForeignKeyConstraint(["store_id"], ["store.id"], name=op.f("fk_voucher_store_id_store")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voucher")),
    )
    op.create_index("ix_voucher_store_period", "voucher", ["store_id", "period"])
    op.create_table(
        "voucher_line",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("voucher_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_key", sa.String(length=64), nullable=False),
        sa.Column("account_code", sa.String(length=32), nullable=False),
        sa.Column("account_name", sa.String(length=128), nullable=False),
        sa.Column("debit", Money4(), nullable=False),
        sa.Column("credit", Money4(), nullable=False),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0)",
            name="voucher_line_one_side",
        ),
        sa.ForeignKeyConstraint(
            ["voucher_id"], ["voucher.id"], name=op.f("fk_voucher_line_voucher_id_voucher")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voucher_line")),
    )
    op.create_index("ix_voucher_line_voucher_id", "voucher_line", ["voucher_id"])


def downgrade() -> None:
    # SQLite drops foreign keys together with the table and cannot ALTER them.
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_voucher_line_voucher_id_voucher", "voucher_line", type_="foreignkey")
    op.drop_index("ix_voucher_line_voucher_id", table_name="voucher_line")
    op.drop_table("voucher_line")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_voucher_store_id_store", "voucher", type_="foreignkey")
    op.drop_index("ix_voucher_store_period", table_name="voucher")
    op.drop_table("voucher")
