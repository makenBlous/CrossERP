"""网页路由包; T33 的装配仍集中在 app.py, 后续任务继续拆分页面。"""

from crosserp.auth.permissions import Permission

PUBLIC = frozenset({"/health", "/login", "/static"})
ROUTE_PERMISSIONS = {
    "/": Permission.REPORT_READ,
    "/imports": Permission.REPORT_READ,
    "/profit": Permission.REPORT_READ,
    "/profit/submit": Permission.APPROVAL_SUBMIT,
    "/vouchers": Permission.REPORT_READ,
    "/vouchers/{voucher_id}": Permission.REPORT_READ,
    "/vouchers/{voucher_id}/download": Permission.VOUCHER_DOWNLOAD,
    "/issues": Permission.REPORT_READ,
    "/approvals": Permission.REPORT_READ,
    "/approvals/{approval_id}": Permission.REPORT_READ,
    "/approvals/{approval_id}/decide": Permission.APPROVAL_DECIDE,
    "/audit": Permission.AUDIT_READ,
    "/audit/verify": Permission.AUDIT_READ,
    "/audit/export": Permission.AUDIT_EXPORT,
    "/security-log": Permission.SECURITY_LOG_READ,
    "/settings": Permission.SETTING_MANAGE,
}
