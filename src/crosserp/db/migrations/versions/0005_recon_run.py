"""对账运行和结果版本。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0005_recon_run"
down_revision: str | Sequence[str] | None = "0004_import_batch_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create recon_run and attach match/issue rows to a run."""
    op.create_table(
        "recon_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("rule_set_version", sa.String(length=32), nullable=False),
        sa.Column("started_at", UtcDateTime(), nullable=False),
        sa.Column("finished_at", UtcDateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("groups_total", sa.Integer(), nullable=False),
        sa.Column("groups_matched", sa.Integer(), nullable=False),
        sa.Column("non_order_lines", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["store_id"], ["store.id"], name=op.f("fk_recon_run_store_id_store")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recon_run")),
    )
    with op.batch_alter_table("recon_run", schema=None) as batch_op:
        batch_op.create_index("ix_recon_run_store_period", ["store_id", "period"], unique=False)
    for table in ("match", "issue"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("recon_run_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_recon_run_id_recon_run",
                "recon_run",
                ["recon_run_id"],
                ["id"],
            )
            batch_op.create_index(f"ix_{table}_recon_run_id", ["recon_run_id"], unique=False)


def downgrade() -> None:
    """Detach results then remove recon_run."""
    connection = op.get_bind()
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        for table in ("issue", "match"):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_constraint(f"fk_{table}_recon_run_id_recon_run", type_="foreignkey")
                batch_op.drop_index(f"ix_{table}_recon_run_id")
                batch_op.drop_column("recon_run_id")
        with op.batch_alter_table("recon_run", schema=None) as batch_op:
            batch_op.drop_constraint("fk_recon_run_store_id_store", type_="foreignkey")
            batch_op.drop_index("ix_recon_run_store_period")
        op.drop_table("recon_run")
    finally:
        if sqlite:
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))
