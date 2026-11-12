"""P1 ingest 疑似重复候选与 SKU 合并字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0040_ing_dedup"
down_revision: str | Sequence[str] | None = "0040_ing_project"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table("sku") as batch:
        batch.add_column(
            sa.Column("source_refs_json", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(sa.Column("merged_into_id", sa.String(64), nullable=True))
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=ON")

    op.create_table(
        "dedup_candidate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("ids", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("merged_target_id", sa.String(64), nullable=True),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'merged', 'rejected')", name="dedup_candidate_status"
        ),
        sa.CheckConstraint(
            "confidence IN ('exact', 'high', 'medium', 'low')",
            name="dedup_candidate_confidence",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dedup_candidate")),
    )
    op.create_index(
        "ix_dedup_candidate_entity_status",
        "dedup_candidate",
        ["entity_type", "status"],
    )
    op.create_index("ix_dedup_candidate_updated_at", "dedup_candidate", ["updated_at"])


def downgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    op.drop_index("ix_dedup_candidate_updated_at", table_name="dedup_candidate")
    op.drop_index("ix_dedup_candidate_entity_status", table_name="dedup_candidate")
    op.drop_table("dedup_candidate")
    with op.batch_alter_table("sku") as batch:
        batch.drop_column("merged_into_id")
        batch.drop_column("source_refs_json")
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=ON")
