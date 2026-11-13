"""清洗问题处理人改为用户标识, 版本与实体版本起点对齐。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_ing_issue_handler"
down_revision: str | Sequence[str] | None = "0041_ing_issue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sqlite_foreign_keys(enabled: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.exec_driver_sql(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}")


def upgrade() -> None:
    _sqlite_foreign_keys(False)
    with op.batch_alter_table("cleansing_issue") as batch:
        batch.alter_column(
            "handler",
            existing_type=sa.String(32),
            type_=sa.String(64),
            existing_nullable=True,
        )
        batch.alter_column(
            "version",
            existing_type=sa.Integer(),
            server_default="0",
            existing_nullable=False,
        )
    _sqlite_foreign_keys(True)


def downgrade() -> None:
    _sqlite_foreign_keys(False)
    with op.batch_alter_table("cleansing_issue") as batch:
        batch.alter_column(
            "version",
            existing_type=sa.Integer(),
            server_default="1",
            existing_nullable=False,
        )
        batch.alter_column(
            "handler",
            existing_type=sa.String(64),
            type_=sa.String(32),
            existing_nullable=True,
        )
    _sqlite_foreign_keys(True)
