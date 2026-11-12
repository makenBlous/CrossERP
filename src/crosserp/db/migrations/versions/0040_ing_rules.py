"""P1 映射规则版本的更新时间和来源身份。"""

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0040_ing_rules"
down_revision: str | None = "0040_ing_core"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("mapping_rule") as batch:
        batch.add_column(sa.Column("updated_at", UtcDateTime(), nullable=True))
        batch.add_column(sa.Column("created_by", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("on_behalf_of", sa.Uuid(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("mapping_rule") as batch:
        batch.drop_column("on_behalf_of")
        batch.drop_column("created_by")
        batch.drop_column("updated_at")
