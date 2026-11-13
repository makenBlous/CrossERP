"""数据范围规则挂到角色并接入店铺授权与智能体收窄表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0027_iam_scope_role"
down_revision: str | Sequence[str] | None = "0042_ing_issue_handler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("iam_data_scope_rule") as batch:
        batch.add_column(sa.Column("role_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_iam_data_scope_rule_role_id_iam_role",
            "iam_role",
            ["role_id"],
            ["id"],
        )
        batch.create_index("ix_iam_data_scope_rule_role_id", ["role_id"])
    op.create_table(
        "user_store_grant",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("granted_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name="fk_user_store_grant_user_id_app_user"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["store.id"], name="fk_user_store_grant_store_id_store"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["app_user.id"], name="fk_user_store_grant_granted_by_app_user"
        ),
        sa.PrimaryKeyConstraint("user_id", "store_id", name="pk_user_store_grant"),
    )
    op.create_table(
        "agent_store_scope",
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["store_id"], ["store.id"], name="fk_agent_store_scope_store_id_store"
        ),
        sa.PrimaryKeyConstraint("agent_id", "store_id", name="pk_agent_store_scope"),
    )


def downgrade() -> None:
    op.drop_table("agent_store_scope")
    op.drop_table("user_store_grant")
    with op.batch_alter_table("iam_data_scope_rule") as batch:
        batch.drop_constraint("fk_iam_data_scope_rule_role_id_iam_role", type_="foreignkey")
        batch.drop_index("ix_iam_data_scope_rule_role_id")
        batch.drop_column("role_id")
