"""将 AI 问答正文改为三库兼容的长文本类型。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0019_llm_text_columns"
down_revision: str | Sequence[str] | None = "0018_prompt_content_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LONG_TEXT = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def upgrade() -> None:
    with op.batch_alter_table("llm_call") as batch_op:
        for column in ("question_text", "answer_text"):
            batch_op.alter_column(
                column,
                existing_type=sa.String(1000000),
                type_=_LONG_TEXT,
                existing_nullable=True,
            )


def downgrade() -> None:
    # MySQL 无法创建历史的 VARCHAR(1000000), 保留 MEDIUMTEXT 才能完成版本回退并继续可用。
    if op.get_bind().dialect.name == "mysql":
        return
    with op.batch_alter_table("llm_call") as batch_op:
        for column in ("question_text", "answer_text"):
            batch_op.alter_column(
                column,
                existing_type=_LONG_TEXT,
                type_=sa.String(1000000),
                existing_nullable=True,
            )
