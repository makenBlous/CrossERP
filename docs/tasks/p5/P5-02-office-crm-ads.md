# 行政、CRM 与广告（P5-02-office-crm-ads 功能包）

- **旧任务卡：** [backend-phases.md P5-02](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

最后接入行政资产/费用、客户与线索、营销活动和广告数据。

## 范围

`admin`、`crm`、`marketing`、`ads`；路径前缀 `/admin/assets`、`/admin/expenses`、`/crm`、`/marketing`、`/ads`。 依据 08 v4 第 5.19 节（office，15 个）、第 5.15 节（crm，24 个）、第 5.14 节（ads，6 个）。

## 涉及实体

`Asset`、`AdministrativeRequest`、`Customer`、`Lead`、`Opportunity`、`AdCampaign`、`AdSpend`。

## 权限与 AI 风险

查询 `none`；客户、线索和商机草稿 `medium`；阶段、活动和工单动作 `low`；回复 `high`；停用/输赢等 `medium`。可撤销，删除统一作废。

## 依赖

P0 权限、P2 工作台/通知、P3 财务。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 行政（08 第 5.19 节）
- CRM 与客服（08 第 5.15 节）
- 广告（08 第 5.14 节）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/integration -k "crm or marketing or ad or administrative" -q` 通过。
2. 角色矩阵和字段策略通过。
3. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
4. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
5. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
6. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
7. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
8. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

客户字段、广告平台和费用科目未定，演示默认值仅用于样例，真实使用前需核实。
