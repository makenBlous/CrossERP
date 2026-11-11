# mypy: ignore-errors
# ruff: noqa

"""播种 IAM 模板角色；角色状态只从数据库读取。"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from crosserp.iam.catalog import load_role_templates

revision: str = "0023_seed_iam_roles"
down_revision: str | Sequence[str] | None = "0022_iam"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TEMPLATE_ROLE_IDS = (
    "owner_manager",
    "store_operator",
    "operations_manager",
    "advertising",
    "product_developer",
    "purchaser",
    "warehouse_logistics",
    "customer_service",
    "accountant",
    "finance_manager",
    "cashier",
    "hr_admin",
    "employee",
    "department_manager",
    "auditor_template",
    "external_viewer",
)
_LEGACY_ROLE_PERMISSIONS = {
    "admin": "owner_manager",
    "operator": (
        "user:read",
        "user:write",
        "report:read",
        "document:read",
        "approval:create",
        "integration:import",
        "agent_tool:read",
    ),
    "finance": (
        "user:read",
        "user:write",
        "report:read",
        "document:read",
        "approval:approve",
        "journal_entry:export",
    ),
    "viewer": ("user:read", "report:read", "document:read", "agent_tool:read"),
    "auditor": (
        "user:read",
        "report:read",
        "document:read",
        "audit_log:read",
        "audit_log:export",
    ),
}
_PARENTS = {
    "operations_manager": ("store_operator",),
    "finance_manager": ("accountant",),
    "department_manager": ("employee",),
}
_SELF_SERVICE_PERMISSIONS = ("user:read", "user:write")


def upgrade() -> None:
    templates = load_role_templates()
    definitions: dict[str, tuple[str, ...]] = {
        role_id: tuple(dict.fromkeys(templates[role_id])) for role_id in _TEMPLATE_ROLE_IDS
    }
    for role_id, permissions in _LEGACY_ROLE_PERMISSIONS.items():
        definitions[role_id] = (
            tuple(dict.fromkeys(templates[permissions]))
            if isinstance(permissions, str)
            else tuple(dict.fromkeys(permissions))
        )
    definitions = {
        role_id: tuple(dict.fromkeys((*permissions, *_SELF_SERVICE_PERMISSIONS)))
        for role_id, permissions in definitions.items()
    }

    role_table = sa.table(
        "iam_role",
        sa.column("id", sa.Uuid()),
        sa.column("slug", sa.String(64)),
        sa.column("name", sa.String(128)),
        sa.column("parent_ids", sa.JSON()),
        sa.column("permissions", sa.JSON()),
        sa.column("data_scopes", sa.JSON()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_template", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    permission_table = sa.table(
        "iam_role_permission",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission", sa.String(128)),
        sa.column("effect", sa.String(8)),
    )
    inheritance_table = sa.table(
        "iam_role_inheritance",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("parent_role_id", sa.Uuid()),
    )
    now = datetime.now(UTC)
    role_ids = {role_id: uuid4() for role_id in definitions}
    op.bulk_insert(
        role_table,
        [
            {
                "id": role_ids[role_id],
                "slug": role_id,
                "name": role_id,
                "parent_ids": list(_PARENTS.get(role_id, ())),
                "permissions": {permission: "allow" for permission in permissions},
                "data_scopes": ["all"],
                "is_active": True,
                "is_template": role_id in _TEMPLATE_ROLE_IDS,
                "created_at": now,
                "updated_at": now,
            }
            for role_id, permissions in definitions.items()
        ],
    )
    op.bulk_insert(
        permission_table,
        [
            {
                "id": uuid4(),
                "role_id": role_ids[role_id],
                "permission": permission,
                "effect": "allow",
            }
            for role_id, permissions in definitions.items()
            for permission in permissions
        ],
    )
    op.bulk_insert(
        inheritance_table,
        [
            {
                "id": uuid4(),
                "role_id": role_ids[role_id],
                "parent_role_id": role_ids[parent],
            }
            for role_id, parents in _PARENTS.items()
            for parent in parents
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM iam_role_inheritance"))
    bind.execute(sa.text("DELETE FROM iam_role_permission"))
    bind.execute(sa.text("DELETE FROM iam_role"))
