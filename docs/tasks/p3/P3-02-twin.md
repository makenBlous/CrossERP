# 数字孪生与推演副本（P3-02-twin 功能包）

- **旧任务卡：** [backend-phases.md P3-02](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

在副本上快照、试算和比较偏差，满意后只生成草稿走原审批链；推演不能直接改正式账。

## 范围

`twin`；路径前缀 `/twin/snapshots`、`/twin/scenarios`、`/twin/drifts`、`/twin/compare`。 依据 08 v4 第 5.25 节（twin，15 个）、第 9.5 节。

## 涉及实体

`TwinSnapshot`、`TwinScenario`、`TwinDrift`、`EntityVersion`。

## 权限与 AI 风险

快照、试算和归档 `low`；偏差处理和转交 `medium`；场景转草稿 `high`，按原动作重新检查权限和风险。

## 依赖

P2-01 库存流水、P0-03、P3-01 草稿接口。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 快照与场景（08 第 5.25 节）
- 偏差处理与转交
- 场景转草稿

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/integration tests/web -k "twin or scenario or drift" -q` 通过。
2. 推演期间正式库无写入（有测试）。
3. 转草稿重新走权限、风险和审批。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

同步频率（库存每日、物流每 6 小时、银行每日）是演示默认值（08 第 12.2 节第 5 条）；推演转草稿是否限定主管（第 7 条）待拍板。
