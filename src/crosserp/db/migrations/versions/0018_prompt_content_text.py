"""将提示词正文改为三库兼容的长文本类型。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0018_prompt_content_text"
down_revision: str | Sequence[str] | None = "0017_eval_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LONG_TEXT = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def upgrade() -> None:
    with op.batch_alter_table("prompt_version") as batch_op:
        batch_op.alter_column(
            "content",
            existing_type=sa.String(100000),
            type_=_LONG_TEXT,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("prompt_version") as batch_op:
        batch_op.alter_column(
            "content",
            existing_type=_LONG_TEXT,
            type_=sa.String(100000),
            existing_nullable=False,
        )
