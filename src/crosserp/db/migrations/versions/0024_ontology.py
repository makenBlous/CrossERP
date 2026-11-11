"""实体目录、动作执行和版本链。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0024_ontology"
down_revision: str | Sequence[str] | None = "0021_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_at", UtcDateTime(), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("on_behalf_of", sa.Uuid(), nullable=True),
        sa.Column("delegation_id", sa.String(64), nullable=True),
        sa.Column("run_id", sa.String(64), nullable=True),
        sa.Column("is_subagent", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("channel", sa.String(32), server_default="web", nullable=False),
        sa.Column("action_id", sa.String(128), nullable=True),
        sa.Column("source_batch_id", sa.Uuid(), nullable=True),
        sa.Column("source_raw_row_id", sa.BigInteger(), nullable=True),
        sa.Column("source_file", sa.String(512), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("diff_json", sa.JSON(), nullable=True),
        sa.Column("audit_log_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_version")),
        sa.UniqueConstraint("entity_type", "entity_id", "version", name="uq_entity_version_number"),
    )
    op.create_index(
        "ix_entity_version_entity", "entity_version", ["entity_type", "entity_id", "version"]
    )
    op.create_index("ix_entity_version_batch", "entity_version", ["source_batch_id"])

    op.create_table(
        "action_execution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("action_id", sa.String(128), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("approval_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_execution")),
        sa.UniqueConstraint("idempotency_key", name="uq_action_execution_idempotency"),
    )
    op.create_index("ix_action_execution_entity", "action_execution", ["entity_type", "entity_id"])

    op.create_table(
        "entity_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("action_id", sa.String(128), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_event")),
    )
    op.create_index(
        "ix_entity_event_entity", "entity_event", ["entity_type", "entity_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_entity_event_entity", table_name="entity_event")
    op.drop_table("entity_event")
    op.drop_index("ix_action_execution_entity", table_name="action_execution")
    op.drop_table("action_execution")
    op.drop_index("ix_entity_version_batch", table_name="entity_version")
    op.drop_index("ix_entity_version_entity", table_name="entity_version")
    op.drop_table("entity_version")
