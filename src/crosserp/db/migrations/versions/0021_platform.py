"""P0 平台底座：文件、任务、关联、密码重置和委托记录。"""  # noqa: RUF002

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0021_platform"
down_revision: str | Sequence[str] | None = "0020_idempotency_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "password_reset_token",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("expires_at", UtcDateTime(), nullable=False),
        sa.Column("used_at", UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_token")),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_token_hash"),
    )
    op.create_table(
        "file_object",
        sa.Column("id", uuid, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("uploaded_by", uuid, nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_file_object")),
        sa.UniqueConstraint("sha256", name="uq_file_object_sha256"),
    )
    op.create_table(
        "job",
        sa.Column("id", uuid, nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.Numeric(6, 5), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(2000), nullable=True),
        sa.Column("result_ref", sa.String(255), nullable=True),
        sa.Column("created_by", uuid, nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("started_at", UtcDateTime(), nullable=True),
        sa.Column("finished_at", UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
    )
    op.create_table(
        "document_link",
        sa.Column("id", uuid, nullable=False),
        sa.Column("from_type", sa.String(64), nullable=False),
        sa.Column("from_id", sa.String(128), nullable=False),
        sa.Column("to_type", sa.String(64), nullable=False),
        sa.Column("to_id", sa.String(128), nullable=False),
        sa.Column("relation", sa.String(64), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_link")),
    )
    op.create_index("ix_document_link_from", "document_link", ["from_type", "from_id"])
    op.create_index("ix_document_link_to", "document_link", ["to_type", "to_id"])
    op.create_table(
        "delegation",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(128), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revoke_reason", sa.String(32), nullable=True),
        sa.Column("expires_at", UtcDateTime(), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delegation")),
    )


def downgrade() -> None:
    op.drop_table("delegation")
    op.drop_index("ix_document_link_to", table_name="document_link")
    op.drop_index("ix_document_link_from", table_name="document_link")
    op.drop_table("document_link")
    op.drop_table("job")
    op.drop_table("file_object")
    op.drop_table("password_reset_token")
