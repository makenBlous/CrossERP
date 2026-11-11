# MCP 只读服务现状与目标

域级权限、风险和 AI 约束见 [`docs/domains/智能体与权限.md`](domains/智能体与权限.md)。

## 当前已实现

`src/crosserp/mcp_server/server.py` 的 `READONLY_TOOLS` 白名单注册 9 个函数：`get_profit`、`list_issues`、`get_order`、`get_settlement`、`get_recon_summary`、`get_approval_status`、`get_voucher`、`compare_profit`、`search_rules_doc`。`create_server()` 使用官方 `FastMCP` 注册这些函数，函数本身通过只读会话访问数据库。

`crosserp mcp serve` 当前只运行 stdio 传输。CLI 在 HTTP 配置未打开时明确拒绝启用 HTTP；不要把未配置的 HTTP 说成已上线。

## 鉴权和边界

外部 MCP 客户端若使用 API Token，Token 由账号页面创建，明文只返回一次，服务端只保存哈希；吊销或账号停用后立即失效。Token、密钥和真实配置不得提交到仓库。当前 MCP 服务的统一用户权限映射、审计字段和委托通行证仍需按 P4 目标接入，状态为**仅设计/未核实**。

## 目标设计

目标是让 MCP、网页、agent、导入投射和定时任务都调用同一实体动作执行器；MCP 只读工具直接查询，写动作必须经过登录人权限、数据范围、状态机、职责分离、审批和唯一写出口。DeerFlow 的进程内工具与外部 MCP 是两条边界，均禁止 AI 执行代码。详见 [`08-后端模块与 API 设计`](design/08-后端模块与API设计.md) 第 4.10、4.11、10 章。
