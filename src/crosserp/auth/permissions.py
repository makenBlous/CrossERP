"""固定角色权限矩阵。"""

from enum import StrEnum

from crosserp.auth.roles import Role


class Permission(StrEnum):
    REPORT_READ = "report.read"
    ISSUE_HANDLE = "issue.handle"
    IMPORT_RUN = "import.run"
    VOUCHER_DRAFT = "voucher.draft"
    APPROVAL_SUBMIT = "approval.submit"
    APPROVAL_DECIDE = "approval.decide"
    VOUCHER_DOWNLOAD = "voucher.download"
    AI_ASK = "ai.ask"
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    SECURITY_LOG_READ = "security_log.read"
    LLM_MONITOR_READ = "llm_monitor.read"
    USER_MANAGE = "user.manage"
    SETTING_MANAGE = "setting.manage"
    BUDGET_MANAGE = "budget.manage"


ROLE_PERMISSIONS = {
    Role.ADMIN: frozenset(Permission),
    Role.FINANCE: frozenset(
        {
            Permission.REPORT_READ,
            Permission.APPROVAL_DECIDE,
            Permission.VOUCHER_DOWNLOAD,
            Permission.AI_ASK,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            Permission.REPORT_READ,
            Permission.ISSUE_HANDLE,
            Permission.IMPORT_RUN,
            Permission.VOUCHER_DRAFT,
            Permission.APPROVAL_SUBMIT,
            Permission.AI_ASK,
        }
    ),
    Role.VIEWER: frozenset({Permission.REPORT_READ, Permission.AI_ASK}),
    Role.AUDITOR: frozenset(
        {
            Permission.REPORT_READ,
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
            Permission.SECURITY_LOG_READ,
            Permission.LLM_MONITOR_READ,
        }
    ),
}


def has_permission(roles: set[str] | tuple[str, ...], permission: Permission | str) -> bool:
    wanted = Permission(permission)
    return any(wanted in ROLE_PERMISSIONS.get(Role(role), frozenset()) for role in roles)
