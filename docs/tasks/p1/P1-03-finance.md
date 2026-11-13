# 结算对账快赢接口（P1-03-finance 功能包）

- **旧任务卡：** [backend-phases.md P1-03](../_archive/backend-phases.md)（已归档）；仓库外：P1-FIN-COMMON、TASK-p1-fin-*、TASK-merge-p1-fin.draft
- **状态：** 已开发的 6 个功能已合入 main（`050e9f5`）；财务导入、费用列映射未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

把已有确定性结算、对账、异常、利润、科目、汇率和导出服务包成 `/api/v1` JSON，核心计算不重写，财务页面最快接上真实数据。

## 范围

`settlement`、`reconciliation`、`profit`、`issues`；路径前缀 `/finance/imports`、`/finance/settlements`、`/finance/recon-runs`、`/finance/issues`、`/finance/profit`、`/finance/accounts`、`/finance/fx-rates`、`/finance/exports`。08 第 5.10 节（34 个接口，其中「来源 = 已有」的 24 个快赢）。新表迁移 `0050_fin_*`。

## 涉及实体

`Settlement`、`SettlementLine`、`ReconRun`、`ReconciliationMatch`、`ReconIssue`、`ProfitView`、`Account`、`FxRate`、`ExportPackage`。

## 权限与 AI 风险

计算、匹配、差异分析和利润/凭证/余额查询 `none`；重跑对账 `low`；处理差异 `medium`；生成凭证、调账和汇率/费用映射修改 `high`；凭证导出 `critical`。AI 只能起草/待审或禁用。

## 依赖

P0 全部；fin-imports、fin-feemap 依赖 P1-02。

## 功能拆分（每个功能一个文件、一个工作树）

- [P1-03-settle](P1-03-settle.md)
- [P1-03-recon](P1-03-recon.md)
- [P1-03-reconissue](P1-03-reconissue.md)
- [P1-03-profit](P1-03-profit.md)
- [P1-03-ref](P1-03-ref.md)
- [P1-03-exports](P1-03-exports.md)
- [P1-03-imports](P1-03-imports.md)
- [P1-03-feemap](P1-03-feemap.md)

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/unit tests/integration tests/web -k "recon or profit or issue or settlement" -q` 通过。
2. golden 逐分一致；未匹配项 100% 有原因码。
3. 统一一个 Decimal→amountMinor 函数（quantize，舍入以 08 为准），无 `int()` 截断。
4. 所有按店铺划分的财务数据经 `store_scope` 过滤；期间、法人范围在 IAM 扩展，不在财务模块另写。
5. 每个端点都有跨店铺（404、403）和跨用户回放测试；全量测试写明总数。
6. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
7. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
8. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
9. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
10. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
11. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

settle `740ac97`、recon `67f3bb1`、reconissue `199d1b3`、profit `faa81e0`、ref `67df14a`、exports `d3a6926` 已合回 `050e9f5`。工作树已拆。财务导入和费用列映射仍未开工。

## 待定 / 需拍板

会计科目、汇兑损益和期间使用演示默认值（08 第 12.2 节第 1 条），真实使用前需核实。
