# mypy: ignore-errors

"""P0 IAM 权限目录、角色和复核对象。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0022_iam"
down_revision: str | Sequence[str] | None = "0020_idempotency_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id():
    return sa.Column("id", sa.Uuid(), primary_key=True, nullable=False)


def _common(table: str, columns: list[sa.Column]) -> None:
    op.create_table(table, _id(), *columns)


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column("permission_version", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("user_role") as batch:
        batch.alter_column(
            "role", existing_type=sa.String(length=16), type_=sa.String(length=64), nullable=False
        )
    _common(
        "iam_role",
        [
            sa.Column("slug", sa.String(64), nullable=False, unique=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("parent_ids", sa.JSON(), nullable=False),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("data_scopes", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_template", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", UtcDateTime(), nullable=False),
            sa.Column("updated_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_permission_override",
        [
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
            sa.Column("permission", sa.String(128), nullable=False),
            sa.Column("effect", sa.String(8), nullable=False),
            sa.Column("reason", sa.String(512), nullable=False),
            sa.Column("data_scopes", sa.JSON(), nullable=False),
            sa.Column("starts_at", UtcDateTime()),
            sa.Column("expires_at", UtcDateTime()),
            sa.Column("created_by", sa.Uuid()),
            sa.Column("created_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_temporary_grant",
        [
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
            sa.Column("permission", sa.String(128), nullable=False),
            sa.Column("effect", sa.String(8), nullable=False),
            sa.Column("reason", sa.String(512), nullable=False),
            sa.Column("starts_at", UtcDateTime(), nullable=False),
            sa.Column("expires_at", UtcDateTime(), nullable=False),
            sa.Column("revoked_at", UtcDateTime()),
            sa.Column("created_by", sa.Uuid()),
            sa.Column("created_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_field_policy",
        [
            sa.Column("field_key", sa.String(128), nullable=False, unique=True),
            sa.Column("permission", sa.String(128), nullable=False),
            sa.Column("masked", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("updated_by", sa.Uuid()),
            sa.Column("updated_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_data_scope_rule",
        [
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("entity", sa.String(128), nullable=False),
            sa.Column("scope_type", sa.String(32), nullable=False),
            sa.Column("values", sa.JSON(), nullable=False),
            sa.Column("updated_by", sa.Uuid()),
            sa.Column("updated_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_access_review",
        [
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
            sa.Column("state", sa.String(16), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("reviewed_by", sa.Uuid()),
            sa.Column("reviewed_at", UtcDateTime()),
            sa.Column("created_at", UtcDateTime(), nullable=False),
        ],
    )
    _common(
        "iam_sod_rule",
        [
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("updated_by", sa.Uuid()),
            sa.Column("updated_at", UtcDateTime(), nullable=False),
        ],
    )
    op.create_table(
        "iam_module_switch",
        sa.Column("module", sa.String(64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Uuid()),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
    )
    op.create_table(
        "iam_dictionary",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Uuid()),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "iam_dictionary",
        "iam_module_switch",
        "iam_sod_rule",
        "iam_access_review",
        "iam_data_scope_rule",
        "iam_field_policy",
        "iam_temporary_grant",
        "iam_permission_override",
        "iam_role",
    ):
        op.drop_table(table)
    op.drop_column("app_user", "permission_version")
    with op.batch_alter_table("user_role") as batch:
        batch.alter_column(
            "role", existing_type=sa.String(length=64), type_=sa.String(length=16), nullable=False
        )
