"""店铺实体增加法人责任方和乐观锁版本。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_pf_stores"
down_revision: str | Sequence[str] | None = "0021_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("store", sa.Column("legal_entity", sa.String(length=255), nullable=True))
    op.add_column("store", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("store", "version")
    op.drop_column("store", "legal_entity")
