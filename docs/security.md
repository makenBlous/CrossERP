# CrossERP 权限矩阵

当前角色权限由 `src/crosserp/auth/permissions.py` 固定定义：`admin` 管理系统，`finance` 审批，`operator` 处理导入和异常，`viewer` 只读报表，`auditor` 查看审计和安全日志。

所有受保护网页先检查登录，再检查权限。权限不足返回 403，并写入 `security_event(permission_denied)`；单人模式关闭时提交人不能批准或驳回自己的审批。
