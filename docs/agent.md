# 只读智能体现状与目标

本文只记录当前代码已经核实的能力，以及目标设计的差别。域级权限、风险和人工兜底见 [`docs/domains/智能体与权限.md`](domains/智能体与权限.md)。后端目标以 [`08-后端模块与 API 设计`](design/08-后端模块与API设计.md) 第 4、8、10 章和 [`ontology-entities.yaml`](design/08/ontology-entities.yaml) 为准。

## 当前已实现

`src/crosserp/agent/tools.py` 已核实 9 个只读工具：

- `get_profit(store, period)`：读取已保存利润快照；
- `list_issues(...)`：读取异常目录；
- `get_order(order_no)`：读取订单行；
- `get_settlement(settlement_id)`：读取结算及明细；
- `get_recon_summary(...)`：读取对账运行汇总；
- `get_approval_status(target_type, target_id)`：读取审批状态；
- `get_voucher(voucher_id)`：读取凭证和借贷合计；
- `compare_profit(store, period_a, period_b)`：用 `Decimal` 比较两个利润快照；
- `search_rules_doc(query, k)`：按关键词检索 `docs/rules/*.md`，返回文件和行号。

工具通过 `agent_session()` 使用 `readonly_session()`，不回退到应用写账号。工具返回 `ToolResult(data, citations)`；金额转字符串，计算仍在确定性 Python 代码完成。

`runtime.ask()` 当前读取 `CROSSERP_MODEL_BASE_URL`、`CROSSERP_MODEL`、`CROSSERP_API_KEY`，没有配置完整三项时拒绝调用真实模型。回答经过数字来源校验；当前运行时没有把工具引用自动注入回答校验，因此含未引用数字会拒答。不要把它描述成已完成的引用问答闭环。

网页 `/ask` 和 CLI `crosserp ask` 是现有入口；它们是当前运行时，不代表 P4 的 DeerFlow worker 已部署。

## 与目标设计的差别

目标要求 agent 继承登录人权限，只少不多；主/子智能体使用同一委托和 `ActionDispatcher`，高风险动作只生成草稿，改账最多到待审，高危动作禁用。DeerFlow 以 SDK 嵌入独立 worker，通行证由系统自动签发、静默续期、权限变化时作废；这些均是设计目标，当前代码尚未核实实现。

目标还会把 9 个工具收敛到 5 个进程内工具（描述、查询、预检、执行、溯源），并保留外部 MCP 只读服务作为可选边界。实现时必须保留人工流程、审计和 AI 关闭后的兜底。

## 开发约束

- LLM 不计算、不改写金额、匹配结果、利润或凭证；没有来源的数字必须拒答。
- AI 只能用只读数据库连接查询；任何写动作回到实体动作执行器并走权限、状态、职责分离和审批。
- 不允许 AI 执行代码；脚本只能作为注册函数或 MCP 工具，仍按同一套风险和权限校验。
- 三项模型配置由用户在前端填写时必须加密保存 API Key，不回显、不写日志。具体目标见 [智能体与权限](domains/智能体与权限.md)。
