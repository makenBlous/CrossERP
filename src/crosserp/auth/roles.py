"""CrossERP 固定角色。"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    FINANCE = "finance"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AUDITOR = "auditor"
