# 平台适配器与外部账套（P4-03-connectors-ledger-targets 功能包）

- **旧任务卡：** [backend-phases.md P4-03](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

按文件导入 → Amazon → Shopify → 领星接入平台，并以金蝶、用友顺序提供外部账套适配器。

## 范围

`connectors`、`channels`、`ledger_targets`；路径前缀 `/integrations`、`/connectors`、`/ledger/targets`。适配器通过 manifest/entry point 注册，设置页按 schema 生成表单。 依据 08 v4 第 5.21 节（integ，13 个）、第 4.11 节。

## 涉及实体

`Connector`、`ImportBatch`、`Settlement`、`LedgerTarget`、`ExportArtifact`、`ApprovalChannel`。

## 权限与 AI 风险

连接器配置和密钥读取仅管理员真人；导入投射 `medium`；预览和测试 `low`；平台授权、账套目标配置和外部写账 `critical`，只能经审批和 `ledger/write_service.py`。

## 依赖

P1-02、P3-01、P4-01。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 适配器接口与配置 schema
- Amazon / Shopify / 领星适配器（按顺序）
- 金蝶 xlsx 账套目标、用友预留

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/integration tests/guard tests/web -k "connector or ledger_target or export" -q` 通过。
2. 没有审批不能导出；密钥不回显、不进日志。
3. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
4. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
5. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
6. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
7. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
8. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

平台账号、API 资格（08 第 12.2 节第 2 条）和真实金蝶/用友模板未核实，演示只使用文件和当前 xlsx 模板。
