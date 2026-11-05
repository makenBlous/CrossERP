"""网页路由包; T33 的装配仍集中在 app.py, 后续任务继续拆分页面。"""

from crosserp.auth.permissions import Permission

PUBLIC = frozenset({"/health", "/login", "/static"})
ROUTE_PERMISSIONS = {
    "/": Permission.REPORT_READ,
    "/imports": Permission.REPORT_READ,
    "/profit": Permission.REPORT_READ,
    "/issues": Permission.REPORT_READ,
    "/security-log": Permission.SECURITY_LOG_READ,
    "/settings": Permission.SETTING_MANAGE,
}
