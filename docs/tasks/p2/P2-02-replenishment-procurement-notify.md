# 补货、采购与站内通知（P2-02-replenishment-procurement-notify 功能包）

- **旧任务卡：** [backend-phases.md P2-02](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

打通「补货 → 采购 → 收货 → 头程 → 出库」，并提供站内待办和工作台。

## 范围

`replenishment`、`procurement`、`notifications`、`workspace`；路径前缀 `/replenishment`、`/procurement`、`/notifications`、`/workspace`。补货计算、到岸成本相关口径见 [07 设计](../../design/07-成本记账与补货计划补齐.md)。 依据 08 v4 第 5.7 节（补货部分）、第 5.8 节（proc，32 个）、第 5.17 节（notify 的站内部分）、第 5.4 节（dash，10 个）；补货计算见 07 设计。

## 涉及实体

`ReplenishmentPlan`、`PurchaseRequest`、`PurchaseOrder`、`GoodsReceipt`、`Notification`、`Task`。

## 权限与 AI 风险

计划试算 `low`；采购、合同、询价和退货草稿多为 `medium`；供应商维护、收货、提交和争议处理 `high`；采购订单取消 `critical`。审批不设金额上限。

## 依赖

P2-01、P0-03。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 补货计划与试算（08 第 5.7 节补货部分 + 07 设计）
- 供应商与采购单（08 第 5.8 节）
- 收货与退货（08 第 5.8 节）
- 站内通知与工作台（08 第 5.17、5.4 节）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/integration -k "replenish or procurement or notification" -q` 通过。
2. 采购状态机非法跳转返回统一错误；计划版本可追溯。
3. 通知查询与已读动作按本人范围；P1-02-issue 的转交改为生成真实站内通知。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

补货阈值和采购审批模板使用演示默认值，真实使用前需核实。
