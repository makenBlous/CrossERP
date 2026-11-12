# 资金、总账、核销与税务（P3-01-finance-ledger-tax 功能包）

- **旧任务卡：** [backend-phases.md P3-01](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

接入应收应付、核销、清分、总账、成本、税务、费用报销和预算；全部按 high 处理，只能经 ledger 写账。

## 范围

`finance`、`ledger`、`tax`、`expense`、`budget`；路径前缀 `/finance/receivables`、`/finance/payables`、`/finance/writeoffs`、`/ledger`、`/tax`、`/expenses`、`/budgets`。07 设计新增的到岸成本分摊、暂估差额、计价明细账、库存总账核对、冲销、期初、反结账审批、结算差额见 [07 设计](../../design/07-成本记账与补货计划补齐.md)。 依据 08 v4 第 5.10 节（其余结算与资金）、第 5.11 节（gl，31 个）、第 5.12 节（tax，6 个）、第 5.13 节（exp，24 个）；成本核算与记账补齐见 07 设计。

## 涉及实体

`Receivable`、`Payable`、`Writeoff`、`Voucher`、`VoucherLine`、`TaxRule`、`ExpenseClaim`、`Budget`。

## 权限与 AI 风险

所有查询 `none`；生成凭证、调账、过账、付款和核销等写账多为 `high`；凭证导出 `critical`；AI 只能起草/待审。

## 依赖

P1-03、P2-01、P0-03；唯一写出口 `ledger/write_service.py`。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 应收应付、核销、清分（08 第 5.10 节其余部分）
- 总账与凭证、成本核算（08 第 5.11 节 + 07 设计）
- 税务（08 第 5.12 节）
- 费用报销与预算（08 第 5.13 节）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/guard tests/integration tests/web -k "ledger or voucher or finance" -q` 通过。
2. 未审批写出返回 403；借贷逐分平衡。
3. 账务写入只经 `ledger/write_service.py`（全仓 grep 无第二写出口）。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

科目编码、汇兑损益和税率使用演示默认值（08 第 12.2 节第 1 条），真实使用前需核实；外部账套先金蝶、再用友。
