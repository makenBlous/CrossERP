# 数据库账号与权限

本文状态：**已实现部分 + 仅设计目标**。

当前代码已有应用用户、角色、会话、API Token 和只读 agent 数据访问的边界；实际授权逻辑以 `src/crosserp/auth/` 和 `src/crosserp/agent/db.py` 为准。正式部署目标是 MySQL 8.4 内网单法人。

## 目标账号

建议至少拆分：应用读写账号、迁移账号、只读 agent worker 账号和运维账号。agent 账号只授予业务查询所需 `SELECT`，不授予 DDL、写业务表、写凭证或写审批的权限；写账仍只能由应用服务调用 `ledger/write_service.py`。

账号、字符集、`STRICT_TRANS_TABLES` 和最小权限清单以 [08 第 11 章](design/08-后端模块与API设计.md) 为准。具体生产账号名、密码和内网地址不写入仓库。
