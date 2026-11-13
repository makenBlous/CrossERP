"""按设计更新模板角色的默认数据范围。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from crosserp.iam.catalog import load_role_template_scopes

revision: str = "0028_role_template_scopes"
down_revision: str | Sequence[str] | None = "0027_iam_scope_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    scopes = load_role_template_scopes()
    bind = op.get_bind()
    role = sa.table(
        "iam_role",
        sa.column("id", sa.Uuid()),
        sa.column("slug", sa.String()),
        sa.column("is_template", sa.Boolean()),
        sa.column("data_scopes", sa.JSON()),
    )
    for slug, tokens in scopes.items():
        role_id = bind.execute(sa.select(role.c.id).where(role.c.slug == slug)).scalar_one()
        bind.execute(
            role.update()
            .where(role.c.id == role_id)
            .where(role.c.is_template.is_(True))
            .values(data_scopes=list(tokens))
        )


def downgrade() -> None:
    bind = op.get_bind()
    role = sa.table(
        "iam_role",
        sa.column("slug", sa.String()),
        sa.column("is_template", sa.Boolean()),
        sa.column("data_scopes", sa.JSON()),
    )
    scopes = load_role_template_scopes()
    for slug in scopes:
        bind.execute(
            role.update()
            .where(role.c.slug == slug)
            .where(role.c.is_template.is_(True))
            .values(data_scopes=["all"])
        )
