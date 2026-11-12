"""P1 投射结果、规则版本溯源和替代补偿记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0040_ing_project"
down_revision: str | Sequence[str] | None = "0040_ing_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("entity_version") as batch:
        batch.add_column(sa.Column("source_rule_version", sa.String(64), nullable=True))

    op.create_table(
        "ingest_projection",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("action_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("undo_payload_json", sa.JSON(), nullable=True),
        sa.Column("compensated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("compensated_at", UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batch.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_row.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_projection")),
        sa.UniqueConstraint(
            "batch_id",
            "raw_record_id",
            "rule_version",
            "action_id",
            name="uq_ingest_projection_source_rule_action",
        ),
    )
    op.create_index("ix_ingest_projection_batch", "ingest_projection", ["batch_id"])
    op.create_index(
        "ix_ingest_projection_entity", "ingest_projection", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_projection_entity", table_name="ingest_projection")
    op.drop_index("ix_ingest_projection_batch", table_name="ingest_projection")
    op.drop_table("ingest_projection")
    with op.batch_alter_table("entity_version") as batch:
        batch.drop_column("source_rule_version")
