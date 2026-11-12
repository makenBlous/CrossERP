# T20 利润计算：订单行 / SKU 利润（成本按生效期、月汇率折人民币）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 2 天 | T18 | `task/T20-profit` |

## 目标
对一个店铺一个月，算出每个订单行和每个内部 SKU 的利润（原币 + 人民币），每一分钱可追溯到结算行和成本/汇率记录；缺成本、缺汇率时开异常，**绝不猜**。

## 背景
- 实施方案 6.3（成本口径）、6.4（利润伪代码）、4 节 `profit_snapshot`、8 W3 第 2 条；指标 3（利润误差 0：与 maken 手算逐分一致）。
- 6.4 公式：`profit = revenue(principal + shipping_charge) + promo + fees(commission + fba + other_fee) + refunds − cogs − freight − ads`；`cogs = qty_net × 订单日期有效的 unit_cost`，`freight = qty_net × freight_per_unit`；广告 v0.5 才有，报表写「未含广告」。费用、促销、退款在结算里本身是负数（按原符号相加，不取反；以 T10 存储符号为准，单测锁定）。
- 退货是否回库（影响 `qty_net`）**待真实数据验证**（实施方案原话）。

## 范围
- 口径（推断部分已标，PR 里请 maken 确认）：
  - **期间归属**：利润按「本期结算里的行」算（与对账同一批结算，`settlement.period_end` 落在本月）。还没结算的订单不进本期利润（推断）。
  - `qty_sold` = 订单类行数量合计；`qty_refunded` = 退款行数量；`qty_net = qty_sold − qty_refunded_restocked`。配置 `profit.refund_restock`：默认 `false`（退款不冲回成本，即 `qty_net = qty_sold`，保守口径；**待 maken 确认**）。
  - **拒付**按退款类计入 `refunds`（T08），成本处理同退款。
  - **Shopify**：打款行无 SKU，按订单行 `item_price` 占比把该订单的收入/费用分摊到各 SKU；分摊产生的尾差（最后 0.0001 级别）全部放到金额最大的那一行，保证 Σ 分摊 = 原值（推断）。
  - **非订单费用**（月租、仓储费、无订单号的调整）：v0.1 **不分摊到 SKU**，在店铺层面单列「未分摊费用」，保证「Σ SKU 利润 + 未分摊费用 = 店铺本期利润」（推断：6.4 伪代码有 `unmatched_fee_lines_allocated(sku)`，但没写分摊规则；分摊方法等 maken 定）。
  - **未匹配的组**照样计入利润（钱确实收了/扣了），但该行标记 `matched=False`，报表里可筛。SKU 未映射的行归到 `internal_sku = "(未映射)<平台SKU>"`。
  - **缺成本**：该订单行 `cogs`、`freight` 为 `None`，开 `COST_MISSING`，该 SKU 利润为 `None`（报表显示「缺成本」），**不当 0 算**。
  - **缺汇率**：`fx_rate(period, from_ccy, "CNY")` 不存在 → `profit_cny = None`，开 `FX_MISSING`（每个 store+period+币种只开一条）；原币利润照常算。CNY 店铺汇率恒为 1，不查表。
  - **舍入**：全程 `Decimal` 不舍入；只在最终输出：`profit = round2(profit_exact)`，`profit_cny = round2(profit_exact × fx_rate)`（**不是**先舍入再乘），`ROUND_HALF_UP`。各分项展示时也各自 round2，因此「分项展示值相加」可能和展示的 profit 差 0.01——这是预期，报表说明里写清楚（推断，maken 手算时用同一规则；不同意就在 PR 里改成「先舍入分项再相加」）。
- `profit/calc.py`（纯函数）：`order_line_profit(lines, order_line, cost, fx) -> LineProfit`；`sku_profit(line_profits) -> SkuProfit`；`period_report(store, period, ...) -> PeriodReport`（含 SKU 列表、未分摊费用、店铺合计、`ads_included=False`）。
- `profit/inputs.py`：`inputs_hash = sha256("\n".join(sorted(输入记录 id)) + "\n" + CALC_VERSION)`；输入记录 = 用到的 settlement_line、order_line、sku_cost、fx_rate 的 id。`CALC_VERSION` 常量（如 `"0.1.0"`），口径一改就升。
- `profit_snapshot` 补列（迁移 `000x_profit_snapshot_cols`）：`qty_sold`、`qty_refunded`、`qty_net`（Integer）、`promotion`（Money4）、`fx_rate`（FxRate NULL）、`profit_cny`（Money4 NULL，存最终 2 位值）、`ads_included`（Boolean）、`status`（ok/cost_missing/fx_missing）、`recon_run_id`。原币金额列存**未舍入**的精确值（Money4 4 位够用：输入最多 4 位，加减乘整数不增加位数）。
- `profit/service.py`：`compute_and_save(session, store_id, period) -> PeriodReport`；同 store+period+calc_version+inputs_hash 已有快照 → 直接复用；输入变了 → 新快照（旧的保留）。

## 不做
- 广告费（v0.5）、非订单费用分摊、多币种之间互转（只做 原币→CNY）。
- xlsx/网页输出（T22/T23）。

## 步骤
1. 先写测试：
   - `tests/unit/profit/test_calc.py`：手写 3–5 个订单行（含退款、部分退款、拒付、缺成本、两段成本生效期跨订单日期、EUR 店铺），期望值**在测试文件里手算写死**，每个期望值旁注释算式。
   - `tests/property/test_profit_props.py`：Σ SKU 利润 + 未分摊费用 = 店铺合计（精确值）；Shopify 分摊后 Σ = 原值；同输入 inputs_hash 相同，任一输入 id 变化 hash 变化。
   - 源码扫描测试（已有的 `float(` 扫描）覆盖 `profit/`。
2. 迁移 + calc + service。
3. 临时 CLI `crosserp profit --period 2026-10 [--store X]` 打印店铺合计和前 10 个 SKU（T22 做 xlsx）。

## 涉及文件
`src/crosserp/profit/{__init__,calc,inputs,service}.py` `src/crosserp/db/repo/profit.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_profit_snapshot_cols.py` `src/crosserp/cli.py` `tests/unit/profit/*` `tests/property/test_profit_props.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/profit tests/property -q` | passed |
| `uv run pytest -m db -k profit -q`（三库） | passed，三库算出的每个数字完全相同 |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 导入 `fx_rates_missing_eur.csv` 代替正常汇率后 `uv run crosserp profit --period 2026-10` | DE 店铺人民币列为空 + 1 条 `FX_MISSING`，原币利润照常 |
| `uv run mypy` | 0 error |

## maken 人工验收清单
- [ ] `uv run crosserp demo-import && uv run crosserp reconcile --period 2026-10 && uv run crosserp profit --period 2026-10`，挑 1 个 SKU，用计算器按背景里的公式算一遍，看是否一致到分。
- [ ] 回答 PR 里的口径问题：退款是否回库（`refund_restock`）、非订单费用要不要分摊、舍入是「最后舍入」还是「分项先舍入」。**这三个答案也决定你手算 20 个 SKU 时用的规则**（T21）。

## 问题

## 完成记录

- 完成内容：实现纯 Decimal 订单行/SKU 利润计算、成本生效期选择、CNY 月汇率换算、最终两位 ROUND_HALF_UP、缺成本/缺汇率异常；新增 `profit_snapshot` 字段和迁移、输入哈希、快照复用、`crosserp profit` 命令；Shopify 按订单金额比例分摊；非订单费用保留为店铺未分摊费用；退款不冲回成本，拒付按退款计入。
- 修改文件：`src/crosserp/profit/{calc,inputs,service}.py`、`src/crosserp/db/repo/profit.py`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0007_profit_snapshot_cols.py`、`src/crosserp/core/models.py`、`src/crosserp/cli.py`、利润单测/性质/三库集成测试、`CHANGELOG.md`。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 测试结果：SQLite 全量 `198 passed, 2 skipped`，覆盖率 `86.13%`；利润单测/性质测试 `5 passed`；利润集成测试通过；MySQL 8.4 利润定向测试 `1 passed`；PostgreSQL 18 利润定向测试 `1 passed`；`ruff`、`mypy`、`pre-commit`、样本 `--check` 全部通过。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 口径：按已授权推荐采用退款不冲回成本、非订单费用不分摊到 SKU、最终一步 ROUND_HALF_UP；广告未含。
- 偏离计划：T20 未新增依赖；利润快照的旧记录保留，输入哈希变化时新增快照。
