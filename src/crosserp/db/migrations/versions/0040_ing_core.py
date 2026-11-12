"""P1 数据进入链路：批次、原始记录、清洗问题和版本化映射规则。"""  # noqa: RUF002

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0040_ing_core"
down_revision: str | Sequence[str] | None = "0025_agent_undo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("import_batch") as batch:
        batch.add_column(sa.Column("source", sa.String(32), nullable=False, server_default="file"))
        batch.add_column(sa.Column("kind", sa.String(32), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("mapping_rule_version", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("counts_json", sa.JSON(), nullable=False, server_default=sa.text("('{}')"))
        )
        for name in (
            "landed_count",
            "valid_count",
            "duplicate_count",
            "quarantined_count",
            "projected_count",
        ):
            batch.add_column(sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("created_by", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("on_behalf_of", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("supersedes_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("received_at", UtcDateTime(), nullable=True))

    with op.batch_alter_table("raw_row") as batch:
        batch.add_column(sa.Column("sha256", sa.String(64), nullable=True))
        batch.add_column(sa.Column("received_at", UtcDateTime(), nullable=True))

    op.create_table(
        "cleansing_issue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("field", sa.String(128), nullable=True),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("suggestion_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batch.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_row.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cleansing_issue")),
    )
    op.create_index("ix_cleansing_issue_batch_id", "cleansing_issue", ["batch_id"])
    op.create_index("ix_cleansing_issue_raw_record_id", "cleansing_issue", ["raw_record_id"])

    op.create_table(
        "mapping_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(128), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("body_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mapping_rule")),
        sa.UniqueConstraint("rule_key", "rule_version", name="uq_mapping_rule_key_version"),
    )
    op.create_index("ix_mapping_rule_key", "mapping_rule", ["rule_key"])


def downgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    op.drop_table("mapping_rule")
    op.drop_table("cleansing_issue")
    with op.batch_alter_table("raw_row") as batch:
        batch.drop_column("received_at")
        batch.drop_column("sha256")
    with op.batch_alter_table("import_batch") as batch:
        for name in (
            "received_at",
            "supersedes_id",
            "version",
            "on_behalf_of",
            "created_by",
            "projected_count",
            "quarantined_count",
            "duplicate_count",
            "valid_count",
            "landed_count",
            "counts_json",
            "mapping_rule_version",
            "kind",
            "source",
        ):
            batch.drop_column(name)
    if sqlite:
        bind.exec_driver_sql("PRAGMA foreign_keys=ON")
