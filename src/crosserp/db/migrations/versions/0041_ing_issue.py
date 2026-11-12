"""清洗问题处理与转交记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0041_ing_issue"
down_revision: str | Sequence[str] | None = "0040_ing_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cleansing_issue") as batch:
        batch.add_column(sa.Column("handler", sa.String(32), nullable=True))
        batch.add_column(
            sa.Column("agent_attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("assignee_user_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("money_impact", sa.Boolean(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("resolution_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("escalation_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("updated_at", UtcDateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_cleansing_issue_assignee_user_id_app_user",
            "app_user",
            ["assignee_user_id"],
            ["id"],
        )

    op.create_table(
        "cleansing_issue_transfer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("on_behalf_of", sa.Uuid(), nullable=True),
        sa.Column("attempts_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("suggestion_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batch.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["cleansing_issue.id"]),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cleansing_issue_transfer")),
    )
    op.create_index(
        "ix_cleansing_issue_transfer_issue_id",
        "cleansing_issue_transfer",
        ["issue_id"],
    )
    op.create_index(
        "ix_cleansing_issue_transfer_assignee",
        "cleansing_issue_transfer",
        ["assignee_user_id"],
    )


def downgrade() -> None:
    op.drop_table("cleansing_issue_transfer")
    with op.batch_alter_table("cleansing_issue") as batch:
        batch.drop_constraint("fk_cleansing_issue_assignee_user_id_app_user", type_="foreignkey")
        for name in (
            "updated_at",
            "escalation_json",
            "resolution_json",
            "version",
            "money_impact",
            "assignee_user_id",
            "agent_attempts",
            "handler",
        ):
            batch.drop_column(name)
