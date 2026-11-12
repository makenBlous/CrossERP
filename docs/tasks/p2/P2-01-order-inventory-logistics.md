# 订单、库存与物流（P2-01-order-inventory-logistics 功能包）

- **旧任务卡：** [backend-phases.md P2-01](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

打通订单、库存台账、收货、出库、头程和物流状态，是补货、采购和财务成本的数据来源。

## 范围

`sales`、`inventory`、`logistics`；路径前缀 `/sales/orders`、`/inventory`、`/inventory/movements`、`/logistics/shipments`、`/logistics/carriers`。 依据 08 v4 第 5.6 节（sales，12 个）、第 5.7 节（inv，28 个，库存部分）、第 5.9 节（logi，17 个）。

## 涉及实体

`SalesOrder`、`SalesOrderLine`、`InventoryPosition`、`StockMovement`、`Warehouse`、`Shipment`、`Carrier`。

## 权限与 AI 风险

查询 `none`；仓库、库存单据和物流基础资料草稿 `medium`；发货、过账、库存盘点提交等 `high`；库存盘点过账 `critical`。

## 依赖

P1-01、P1-02、P0-03。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 订单与售后（08 第 5.6 节）
- 仓库与库存台账、移动加权流水（08 第 5.7 节库存部分）
- 盘点与过账（08 第 5.7 节）
- 物流与头程（08 第 5.9 节）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/integration -k "order or inventory or logistics" -q` 通过。
2. 并发状态转移幂等；状态机非法跳转返回统一错误。
3. 移动加权库存流水逐分正确，金额无浮点。
4. 所有按店铺划分的数据经 `store_scope` 过滤。
5. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
6. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
7. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
8. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
9. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
10. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

库存计价和物流时区采用演示默认值，真实使用前需核实。
