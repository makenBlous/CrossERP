"""W5 登录和权限安全事件哈希链。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.db.types import UtcDateTime

revision: str = "0013_security_event"
down_revision: str | Sequence[str] | None = "0012_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("ts", UtcDateTime(), nullable=False),
        sa.Column("event", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_event")),
        sa.UniqueConstraint("seq", name=op.f("uq_security_event_seq")),
    )
    op.create_index("ix_security_event_ts", "security_event", ["ts"])
    op.create_index("ix_security_event_user_ts", "security_event", ["user_id", "ts"])
    op.create_index("ix_security_event_event_ts", "security_event", ["event", "ts"])


def downgrade() -> None:
    op.drop_index("ix_security_event_event_ts", table_name="security_event")
    op.drop_index("ix_security_event_user_ts", table_name="security_event")
    op.drop_index("ix_security_event_ts", table_name="security_event")
    op.drop_table("security_event")
