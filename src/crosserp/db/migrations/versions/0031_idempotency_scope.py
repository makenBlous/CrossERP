"""幂等记录按调用身份、方法和路由模板隔离。

已有行没有调用身份. 迁移保留键, 请求体哈希和响应, 并把身份写成
legacy-unscoped. 这个值对不上任何真实调用人, 因此旧记录不会被回放给别人.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_idempotency_scope"
down_revision: str | Sequence[str] | None = "0030_cat_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_IDENTITY = "legacy-unscoped"
_LEGACY_ACTOR_TYPE = "legacy"
_LEGACY_ACTOR_KEY = "unscoped"
_LEGACY_METHOD = "LEGACY"
_LEGACY_ROUTE = "legacy:unscoped"


def _scope_hash(key: str) -> str:
    raw = json.dumps(
        [_LEGACY_IDENTITY, _LEGACY_METHOD, _LEGACY_ROUTE, key],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _q(name: str) -> str:
    return "`" + name + "`"


def _backfill(table: str, key_column: str, *, write_actor_type: bool) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f"SELECT {_q('id')}, {_q(key_column)} AS key_value FROM {_q(table)}")
    ).fetchall()
    actor_sql = "actor_type = :actor_type, " if write_actor_type else ""
    for row in rows:
        key_value = row.key_value
        if key_value is None:
            continue
        bind.execute(
            sa.text(
                f"UPDATE {table} SET caller_identity = :identity, "
                f"represented_user_id = :represented, {actor_sql}"
                "actor_key = :actor_key, http_method = :method, "
                "route_template = :route, idempotency_scope_hash = :digest "
                "WHERE id = :id"
            ),
            {
                "identity": _LEGACY_IDENTITY,
                "represented": _LEGACY_IDENTITY,
                "actor_type": _LEGACY_ACTOR_TYPE,
                "actor_key": _LEGACY_ACTOR_KEY,
                "method": _LEGACY_METHOD,
                "route": _LEGACY_ROUTE,
                "digest": _scope_hash(str(key_value)),
                "id": row.id,
            },
        )


def upgrade() -> None:
    with op.batch_alter_table("idempotency_key") as batch:
        batch.drop_index("ix_idempotency_key_key")
        batch.add_column(sa.Column("caller_identity", sa.String(255), nullable=True))
        batch.add_column(sa.Column("represented_user_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("actor_type", sa.String(16), nullable=True))
        batch.add_column(sa.Column("actor_key", sa.String(128), nullable=True))
        batch.add_column(sa.Column("http_method", sa.String(16), nullable=True))
        batch.add_column(sa.Column("route_template", sa.String(255), nullable=True))
        batch.add_column(sa.Column("idempotency_scope_hash", sa.String(64), nullable=True))
    _backfill("idempotency_key", "key", write_actor_type=True)
    with op.batch_alter_table("idempotency_key") as batch:
        batch.alter_column("caller_identity", existing_type=sa.String(255), nullable=False)
        batch.alter_column("represented_user_id", existing_type=sa.String(64), nullable=False)
        batch.alter_column("actor_type", existing_type=sa.String(16), nullable=False)
        batch.alter_column("http_method", existing_type=sa.String(16), nullable=False)
        batch.alter_column("actor_key", existing_type=sa.String(128), nullable=False)
        batch.alter_column("route_template", existing_type=sa.String(255), nullable=False)
        batch.alter_column("idempotency_scope_hash", existing_type=sa.String(64), nullable=False)
        batch.create_unique_constraint("uq_idempotency_scope_hash", ["idempotency_scope_hash"])

    with op.batch_alter_table("action_execution") as batch:
        batch.drop_constraint("uq_action_execution_idempotency", type_="unique")
        batch.add_column(sa.Column("caller_identity", sa.String(255), nullable=True))
        batch.add_column(sa.Column("represented_user_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("actor_key", sa.String(128), nullable=True))
        batch.add_column(sa.Column("http_method", sa.String(16), nullable=True))
        batch.add_column(sa.Column("route_template", sa.String(255), nullable=True))
        batch.add_column(sa.Column("idempotency_scope_hash", sa.String(64), nullable=True))
    _backfill("action_execution", "idempotency_key", write_actor_type=False)
    with op.batch_alter_table("action_execution") as batch:
        batch.create_unique_constraint("uq_action_execution_scope_hash", ["idempotency_scope_hash"])


def downgrade() -> None:
    with op.batch_alter_table("action_execution") as batch:
        batch.drop_constraint("uq_action_execution_scope_hash", type_="unique")
        batch.drop_column("idempotency_scope_hash")
        batch.drop_column("route_template")
        batch.drop_column("http_method")
        batch.drop_column("actor_key")
        batch.drop_column("represented_user_id")
        batch.drop_column("caller_identity")
        batch.create_unique_constraint("uq_action_execution_idempotency", ["idempotency_key"])
    with op.batch_alter_table("idempotency_key") as batch:
        batch.drop_constraint("uq_idempotency_scope_hash", type_="unique")
        batch.drop_column("idempotency_scope_hash")
        batch.drop_column("route_template")
        batch.drop_column("http_method")
        batch.drop_column("actor_key")
        batch.drop_column("actor_type")
        batch.drop_column("represented_user_id")
        batch.drop_column("caller_identity")
        batch.create_index("ix_idempotency_key_key", ["key"], unique=True)
