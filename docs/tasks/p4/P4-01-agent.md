# 智能体中心与委托通行证（P4-01-agent 功能包）

- **旧任务卡：** [backend-phases.md P4-01](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

在独立 Agent worker 进程和独立 Python 环境中运行 DeerFlow SDK；主、子智能体继承登录人权限，通行证自动签发、续期和作废。

## 范围

`agent`；路径前缀 `/agent/assistants`、`/agent/conversations`、`/agent/suggestions`、`/agent/tools`、`/agent/model-config`、`/agent/delegations`（仅管理员审计读取）。禁止 bash、沙箱和 Docker 代码执行。 依据 08 v4 第 5.22 节（agent，55 个）、第 10 节。

## 涉及实体

`Agent`、`AgentConversation`、`AgentSuggestion`、`RegisteredFunction`、`Delegation`、`ModelConfig`、`LlmCall`。

## 权限与 AI 风险

只读工具 `none`；建议、收件箱确认等 `medium`/`low`（中风险不限次数、可撤销、只进每日摘要）；工具、任务、模型配置等治理写操作 `critical`；改账动作按 `high`/`critical` 仅到起草/待审。

## 依赖

P0-02、P0-03、P3-01；DeerFlow 版本锁定未核实。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- Agent worker 与 DeerFlow SDK 嵌入（08 第 10.1 节）
- 委托通行证中间件（08 第 10.5 节）
- 模型配置与密钥加密存储（08 第 10.8 节）
- 会话、建议、工具注册表（08 第 5.22 节）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/agent tests/guard tests/integration -q` 通过。
2. 权限变化/登出/切换账号立即使旧通行证失效，下次消息静默续签。
3. 子智能体不可扩权；关闭 AI 时所有工具停止。
4. API Key 加密存储、不回显、不进日志。
5. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
6. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
7. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
8. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
9. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
10. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

DeerFlow 正式版本锁定（08 第 12.2 节第 4 条）、worker 共用领域包方式、月度 LLM 预算（第 3 条）待定，真实使用前需核实。
