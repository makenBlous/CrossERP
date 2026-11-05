"""T51 评测运行记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0017_eval_run"
down_revision: str | Sequence[str] | None = "0016_llm_budget"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eval_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ts", UtcDateTime(), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=True),
        sa.Column("git_sha", sa.String(40), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("triggered_by", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_run")),
    )


def downgrade() -> None:
    op.drop_table("eval_run")
