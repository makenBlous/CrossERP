"""P0-03a 统一审计上下文、审批流程与留存索引。"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0024_audit_approval"
down_revision: str | Sequence[str] | None = "0023_seed_iam_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    audit_columns: list[sa.Column[Any]] = [
        sa.Column("agent_id", sa.String(128)),
        sa.Column("on_behalf_of", sa.String(128)),
        sa.Column("delegation_id", sa.String(128)),
        sa.Column("run_id", sa.String(128)),
        sa.Column("tool_call_id", sa.String(128)),
        # JSON keeps the append-only tamper surface portable; new rows write a boolean value.
        # It remains nullable so MySQL can add it to an existing audit chain without a JSON default.
        sa.Column("is_subagent", sa.JSON()),
        sa.Column("subagent_name", sa.String(128)),
        sa.Column("channel", sa.String(32)),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(128)),
        sa.Column("diff_json", sa.JSON()),
        sa.Column("evidence_json", sa.JSON()),
        sa.Column("model", sa.String(128)),
        sa.Column("prompt_version", sa.String(64)),
        sa.Column("llm_call", sa.String(128)),
        sa.Column("confidence", sa.JSON()),
        sa.Column("autonomy_level", sa.String(16)),
    ]
    with op.batch_alter_table("audit_log") as batch:
        for column in audit_columns:
            batch.add_column(column)
    approval_columns: list[sa.Column[Any]] = [
        sa.Column("approval_type", sa.String(64)),
        sa.Column("risk_tier", sa.String(16)),
        sa.Column("actor_type", sa.String(16), nullable=False, server_default="human"),
        sa.Column("on_behalf_of", sa.Uuid()),
        sa.Column("resolution", sa.JSON()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("initiator_confirmed_by", sa.Uuid()),
        sa.Column("initiator_confirmed_at", UtcDateTime()),
        sa.Column("initiator_confirmation_hash", sa.String(64)),
        sa.Column("approver_ids", sa.JSON()),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
    ]
    with op.batch_alter_table("approval") as batch:
        # New lifecycle states such as awaiting_initiator exceed the legacy 16-char width.
        batch.alter_column(
            "state",
            existing_type=sa.String(length=16),
            type_=sa.String(length=32),
            existing_nullable=False,
            nullable=False,
        )
        for column in approval_columns:
            batch.add_column(column)
    op.create_table(
        "approval_type",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("risk_tier", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("template_json", sa.JSON()),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "workflow_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_type", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.Uuid()),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_type", "version", name="uq_workflow_rule_type_version"),
    )
    op.create_table(
        "audit_alert",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("detail_json", sa.JSON()),
        sa.Column("audit_log_id", sa.Uuid()),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.Column("resolved_at", UtcDateTime()),
        sa.Column("resolved_by", sa.Uuid()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "retention_policy",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chain", sa.String(32), nullable=False),
        sa.Column("retain_days", sa.Integer(), nullable=False, server_default="3650"),
        sa.Column("archive_before", UtcDateTime()),
        sa.Column("updated_by", sa.Uuid()),
        sa.Column("updated_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain"),
    )
    op.create_table(
        "audit_archive_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chain", sa.String(32), nullable=False),
        sa.Column("upto_id", sa.Uuid()),
        sa.Column("upto_hash", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_archive_run")
    op.drop_table("retention_policy")
    op.drop_table("audit_alert")
    op.drop_table("workflow_rule")
    op.drop_table("approval_type")
    bind = op.get_bind()
    sqlite_fk = bind.dialect.name == "sqlite"
    if sqlite_fk:
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table("approval") as batch:
        for name in (
            "current_step",
            "approver_ids",
            "initiator_confirmation_hash",
            "initiator_confirmed_at",
            "initiator_confirmed_by",
            "content_hash",
            "resolution",
            "on_behalf_of",
            "actor_type",
            "risk_tier",
            "approval_type",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("audit_log") as batch:
        for name in (
            "autonomy_level",
            "confidence",
            "llm_call",
            "prompt_version",
            "model",
            "evidence_json",
            "diff_json",
            "entity_id",
            "entity_type",
            "channel",
            "subagent_name",
            "is_subagent",
            "tool_call_id",
            "run_id",
            "delegation_id",
            "on_behalf_of",
            "agent_id",
        ):
            batch.drop_column(name)
    if sqlite_fk:
        bind.exec_driver_sql("PRAGMA foreign_keys=ON")
