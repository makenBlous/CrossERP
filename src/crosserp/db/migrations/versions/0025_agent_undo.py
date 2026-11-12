"""P0 L3 动作撤销登记。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0025_agent_undo"
down_revision: str | Sequence[str] | None = "0026_audit_export_file_required"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_undo",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("suggestion_id", sa.Uuid(), nullable=True),
        sa.Column("action_audit_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("action_version", sa.Integer(), nullable=False),
        sa.Column("undo_payload_json", sa.JSON(), nullable=False),
        sa.Column("deadline_at", UtcDateTime(), nullable=False),
        sa.Column("undone_by", sa.Uuid(), nullable=True),
        sa.Column("undone_at", UtcDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_undo")),
    )
    op.create_index("ix_agent_undo_deadline", "agent_undo", ["deadline_at"])
    op.create_index("ix_agent_undo_entity", "agent_undo", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_undo_entity", table_name="agent_undo")
    op.drop_index("ix_agent_undo_deadline", table_name="agent_undo")
    op.drop_table("agent_undo")
