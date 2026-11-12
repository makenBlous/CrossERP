# T18 对账引擎核心：规则注册表 + 订单号/SKU 确定性匹配

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 2 天 | T16, T17 | `task/T18-recon-engine-core` |

## 目标
`reconcile(store, period)` 用确定性规则把结算行组和订单行配上；每个没配上的组都至少有一条带原因码的异常；匹配率按实施方案的口径算出来。

## 背景
- 实施方案 6.2 伪代码、6.1 原因码、4 节 `match` 表、8 W3 第 1 条；指标 2（匹配 ≥95% 且未匹配 100% 有原因）。
- **匹配率口径（实施方案）**：订单类结算行组中已匹配的 ÷ 全部订单类结算行组；非订单行（月租、仓储费等）不进分母，单列。
- Shopify 打款 CSV 的交易行有订单号（`Order` 列）但**没有 SKU**（T11 的 11 个基础列），所以不能按 (order_id, sku) 分组。处理（推断，PR 里请 maken 确认）：Shopify 按 `order_id` 整单分组，与该订单全部订单行的合计比较；SKU 归属留给利润计算（T20 按订单行金额占比分摊）。

## 范围
- 新表（迁移 `000x_recon_run`）：`recon_run(id, store_id, period String(7), as_of Date, rule_set_version String(32), started_at, finished_at, status, groups_total, groups_matched, non_order_lines, created_by)`；`match` 和 `issue` 增加可空列 `recon_run_id`。
  - **重跑**：每次运行新建一个 `recon_run`；同 store+period 的「当前结果」= 最近一次 `status=done` 的 run；旧 run 的 match/issue **保留**（可追溯），查询默认只看当前 run。导入阶段产生的 issue（`recon_run_id IS NULL`）不受重跑影响。（推断：实施方案没写重跑语义，此设计便于审计，PR 里说明。）
- `recon/registry.py`：`Rule` 协议 `{id: str, version: str, applies(group) -> bool, evaluate(ctx, group) -> RuleResult}`；`RuleResult = Matched(order_lines, rule_id, diff) | Unmatched(issues) | Pass`。规则按注册顺序执行，第一个给出 Matched/Unmatched 的规则生效。`rule_set_version` = 所有规则 `id@version` 排序后的 sha256 前 12 位。
- `recon/engine.py`：`reconcile(session, store_id, period, *, as_of=None, grace_days=None) -> ReconResult`，步骤严格按 6.2：
  1. 结算平衡已在导入时检查（`SETTLEMENT_UNBALANCED`），这里**不重复开**，只读出来计入报告。
  2. 取本期结算：`settlement.period_end` 落在 `period` 月内（UTC）的结算（推断，PR 说明）；行分为订单类（`transaction_type` 属于订单/退款/拒付类，集合放 `recon/vocab.py`，取值来自 T10/T11 的 vocab）和非订单类。
  3. 订单类分组：Amazon `(order_id, normalize(sku))`；Shopify `(order_id)`。`normalize` = 去首尾空格 + 大写（推断）。
  4. 订单索引：本店铺 `order_date ∈ [period_start − 60 天, period_end + 60 天]`。
  5. 每组按规则顺序：
     - `R01 sku_mapped`：SKU 不在 `sku` 映射 → `SKU_UNMAPPED`（仅 Amazon）。
     - `R02 order_exists`：订单号不在索引 → 全是退款类行 → `REFUND_WITHOUT_ORDER`，否则 `NOT_IN_ERP`。
     - `R03 currency`：结算行币种 ≠ 订单币种 → `CURRENCY_MISMATCH`。
     - `R04 qty`：Σ订单类行数量（退款行不减数量，部分退款不报 QTY_MISMATCH，见 T08 场景）≠ Σ订单行 qty → `QTY_MISMATCH`。
     - `R05 amount`：Σprincipal（不含退款行）≠ Σ订单行 item_price → `AMOUNT_MISMATCH`，detail 带差额；Shopify 用 `Amount`（毛额）对订单合计。`item_price` 是单价还是行合计，以 T12 `synthetic_orders.yaml` 的定义为准；如果是单价，比较前乘 qty（PR 里写明）。
     - `R06 order_id+sku`（Shopify 为 `order_id`）：以上都过 → `match(status=matched, rule_id, diff=0)`。
   金额比较一律 `Decimal` 精确相等，**没有容差**（要容差先问 maken）。
  6. 断言：每个未匹配组至少 1 条 open issue（`counts_as_unmatched=True` 的码），否则抛 `ReconInvariantError`——这是指标 2「100% 有原因」的代码保证。
- 输出 `ReconResult{run_id, groups_total, groups_matched, match_rate: Decimal, unmatched_by_kind: dict, non_order_lines: list}`；`match_rate` 分母为 0 时为 `None`（不是 100%）。
- 配置：`recon.grace_days`（默认 14）、`recon.order_window_days`（默认 60），从现有配置机制读取。
- `db/repo/recon.py`：所有读写；引擎本身是纯函数为主（输入数据对象，输出结果对象），便于单测。

## 不做
- `NOT_IN_SETTLEMENT` / 待下期、多收费、拒付、重复结算（T19）。
- 利润（T20）、报表与 CLI 展示（T22）。
- 不做模糊匹配、不做 AI 匹配。

## 步骤
1. 先写测试：
   - `tests/unit/recon/test_rules.py`：每条规则用手写小数据各测正反例（不依赖数据库）。
   - `tests/property/test_recon_props.py`（hypothesis）：随机生成订单+结算 → 断言「未匹配组 ⇒ 有 issue」「matched + unmatched = total」「同一输入跑两次结果完全相同（确定性）」。
   - `tests/integration/test_recon_synthetic.py`（三库）：demo-import → `reconcile(US, 2026-10)` → 未匹配的原因码集合与 `anomalies.json` 中对应场景一致；匹配率 = `summary.json` 的预期匹配率。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
2. 迁移 + repo + 引擎。
3. 临时 CLI `crosserp reconcile --period 2026-10 [--store X] [--as-of 2026-10-31]`，只打印 `ReconResult` 摘要（T22 再做完整输出）。

## 涉及文件
`src/crosserp/recon/{__init__,registry,engine,rules,vocab}.py` `src/crosserp/db/repo/recon.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_recon_run.py` `src/crosserp/cli.py` `tests/unit/recon/*` `tests/property/test_recon_props.py` `tests/integration/test_recon_synthetic.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/recon tests/property -q` | passed |
| `uv run pytest -m db -k recon -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run crosserp demo-import && uv run crosserp reconcile --period 2026-10` | 打印每个店铺的组数、匹配数、匹配率、按原因码的未匹配数；美国店匹配率 ≥ 95%（以 summary.json 为准） |
| 再跑一次 `reconcile` | 结果数字完全相同，新增一个 recon_run |
| `uv run mypy` | 0 error |

## maken 人工验收清单
- [ ] `uv run crosserp demo-import`，然后 `uv run crosserp reconcile --period 2026-10`，截图输出，和 `samples/synthetic/EXPECTED.md` 里写的预期匹配率对比。
- [ ] `uv run crosserp issues list --kind NOT_IN_ERP`、`--kind QTY_MISMATCH`，各挑 1 条到原始 tsv 文件里找到那一行，确认原因说得对。
- [ ] 确认 PR 里的两条设计：Shopify 按整单匹配；重跑保留旧结果。

## 问题

## 完成记录

- 完成内容：新增 `recon_run` 运行记录和结果外键；实现 Amazon `(订单号, SKU)`、Shopify `订单号` 的确定性分组匹配；规则注册表提供 `applies/evaluate`、`Matched/Unmatched/Pass` 协议并记录规则集版本；未匹配组统一写入原因码，重跑保留旧运行；新增 `crosserp reconcile` 摘要命令。
- 修改文件：`src/crosserp/recon/registry.py`、`src/crosserp/recon/engine.py`、`src/crosserp/db/repo/recon.py`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0005_recon_run.py`、`src/crosserp/cli.py`、导入/异常服务及迁移守卫测试；新增对账单测、性质测试和合成样本集成测试；更新 `CHANGELOG.md`。
- 测试结果：`.venv/bin/uv run ruff format --check .` 通过；`ruff check .` 通过；`mypy` 通过；`pre-commit run --all-files` 通过；SQLite 全量 `192 passed, 2 skipped`，覆盖率 `85.75%`；MySQL 8.4 定向对账 `1 passed`；PostgreSQL 18 定向对账 `1 passed`；规则/性质/合成集成定向测试 `6 passed`。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 偏离计划：将任务中描述的规则协议完整落地为可执行注册表；`grace_days`、待下期、多收费、拒付、部分退款和重复结算仍按范围留给 T19；当前项目未安装 `gh`，PR 需通过 GitHub 网页创建。
- PR：已推送任务分支后由 maken 在 GitHub 创建/审核；本地合并回 `main`。
