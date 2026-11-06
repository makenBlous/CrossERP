"""T44 AI 调用和工具调用记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

from crosserp.db.types import Money4, UtcDateTime

revision: str = "0015_llm_observability"
down_revision: str | Sequence[str] | None = "0014_voucher"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROMPT_CONTENT = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def upgrade() -> None:
    op.create_table(
        "prompt_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", _PROMPT_CONTENT, nullable=False),
        sa.Column("created_at", UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_version")),
        sa.UniqueConstraint("name", "sha256", name="uq_prompt_version_name_sha256"),
    )
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ts", UtcDateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_estimate", Money4(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("refusal_reason", sa.String(512), nullable=True),
        sa.Column("question_text", _PROMPT_CONTENT, nullable=True),
        sa.Column("answer_text", _PROMPT_CONTENT, nullable=True),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_version.id"],
            name=op.f("fk_llm_call_prompt_version_id_prompt_version"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_call")),
    )
    op.create_table(
        "llm_tool_call",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("llm_call_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=False),
        sa.Column("result_rows", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(
            ["llm_call_id"], ["llm_call.id"], name=op.f("fk_llm_tool_call_llm_call_id_llm_call")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_tool_call")),
    )
    op.create_index("ix_llm_tool_call_llm_call_id", "llm_tool_call", ["llm_call_id"])


def downgrade() -> None:
    # 删除表会一并删除索引; MySQL 不允许先删被外键依赖的索引。
    op.drop_table("llm_tool_call")
    op.drop_table("llm_call")
    op.drop_table("prompt_version")
