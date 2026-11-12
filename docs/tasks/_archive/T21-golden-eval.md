# T21 标准答案比对：利润逐分一致 + 匹配率/异常原因断言（指标 2、3）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1 天 | T19, T20 | `task/T21-golden-eval` |

## 目标
用一条命令把系统结果和**手算的标准答案**逐格对比，差 0.01 也报出来；指标 2、3 变成 CI 里的断言，以后改代码一旦算错就红灯。

## 背景
- 实施方案 6.4（golden：maken 用 Excel 手算 20 个 SKU，测试要求逐分一致）、8 W3 第 7 条、「指标 × 版本 × 证据」表（指标 2、3 的证据都是 golden 测试断言）。
- 标准答案文件格式已在 `docs/sample-data/README.md` 定好：`profit_expected.csv`（period, store, internal_sku, currency, qty_sold, qty_refunded, revenue, promotion, platform_fees, refunds, cogs, freight, ads, profit, fx_rate, profit_cny, note）、`issues_expected.csv`、`settlement_expected.csv`，放在 `samples/real_anonymized/expected/`（不提交）。
- 两套答案：
  1. **合成样本答案** `tests/golden/profit_expected.csv`（提交）：由生成器按「造数据时就知道的真值」写出，**不得调用 `crosserp.profit`**（否则等于自己对自己）。
  2. **maken 手算答案**（真实脱敏数据，20 个 SKU，不提交）：这是指标 3 的正式证据。

## 范围
- `scripts/gen_samples.py` 扩展：按 T20 定下的口径（含 maken 对舍入/回库/分摊的答复），用生成器内部的场景参数独立算出 `samples/synthetic/expected/profit_expected.csv` 和 `issues_expected.csv`，复制到 `tests/golden/`。代码里写一个单独的小函数 `reference_profit()`，只用加减乘和 `Decimal`，不 import `crosserp.profit`（有测试用 AST 检查这一点）。
- `crosserp check-golden --period 2026-10 --expected <profit_expected.csv> [--issues <issues_expected.csv>] [--store X]`：
  - 先确保已 reconcile + profit（没跑就跑）。
  - 逐行（key = period+store+internal_sku）逐列比较，金额按字符串化的 2 位小数**精确相等**；整数列精确相等；`ads` 列期望为空/0 时跳过。
  - 输出：总行数、完全一致行数、差异表（列名、期望、实际、差额、该 SKU 涉及的结算行号），缺行/多行单列。全部一致退出码 0，否则 1。
  - `--issues`：比对异常（key = store+order_id+sku+kind），输出漏报（期望有、系统没有）和多报。
  - 加 `--report-md <path>`：把结果写成 markdown，给 `docs/eval-results/` 用。
- 测试 `tests/golden/test_golden.py`（三库）：【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
  - 利润：系统输出 vs `tests/golden/profit_expected.csv` **全部一致**。
  - 指标 2：每个店铺 `match_rate ≥ 0.95`；所有未匹配组 100% 有 `counts_as_unmatched` 的 open issue；`issues_expected.csv` 无漏报。
  - 若 `samples/real_anonymized/expected/profit_expected.csv` 存在 → 同样比对（本地跑）；不存在 → skip，CI 里自动 skip。
- `docs/eval-results/README.md`：说明怎么生成 `v0.1-golden-<日期>.md`。

## 不做
- 不改利润/对账口径——比对不一致时，先判断是代码错还是答案错，在 PR 里写清楚，**不准为了让测试通过去改期望文件**（除非 maken 确认答案错了）。
- 不做 AI 问答评测（那是 v0.5 的 `eval` 命令，名字不要冲突，所以本命令叫 `check-golden`）。

## 步骤
1. 生成器写 `reference_profit()` 和期望文件；在 `EXPECTED.md` 里给 2 个 SKU 写出完整手算过程（供 maken 抽查）。
2. 写 `check-golden` 和 golden 测试。
3. 如果 golden 不一致：逐项排查，修 bug 或在「问题」里写清楚分歧，状态改 blocked。

## 涉及文件
`scripts/gen_samples.py` `samples/synthetic/expected/*` `samples/synthetic/EXPECTED.md` `tests/golden/*` `src/crosserp/profit/golden.py` `src/crosserp/cli.py` `docs/eval-results/README.md` `tests/unit/test_reference_independent.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/golden -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run crosserp check-golden --period 2026-10 --expected tests/golden/profit_expected.csv` | 「N/N 行完全一致」，退出码 0 |
| 手工把期望文件里一个 profit 改大 0.01 再跑 | 退出码 1，差异表指出那一格 |

## maken 人工验收清单
- [ ] 按 `docs/sample-data/README.md` 的格式，用 Excel 手算 20 个真实 SKU，另存为 UTF-8 CSV 放到 `samples/real_anonymized/expected/profit_expected.csv`（规则用 T20 PR 里你确认的口径）。
- [ ] 导入对应的真实脱敏文件后运行 `uv run crosserp check-golden --period <月份> --expected samples\real_anonymized\expected\profit_expected.csv --report-md docs\eval-results\v0.1-golden-real.md`。
- [ ] 有差异的行：和代理一起看是谁算错了。**指标 3 要求 20/20 完全一致。**
- [ ] 抽查 `EXPECTED.md` 里 2 个合成 SKU 的手算过程，看是否看得懂、算得对。

## 问题

## 完成记录

- 完成内容：新增独立 `profit_expected.csv`（8 个运行 SKU + 12 个 reference-only 合成手算行，共 20 行）、异常标准答案、`crosserp check-golden` 逐格比较和 Markdown 报告；golden 测试覆盖利润逐分一致、异常漏报/多报、故意改大 0.01 必须失败；生成器提供独立参考答案输出，不导入 `crosserp.profit`。
- 修改文件：`src/crosserp/profit/golden.py`、`src/crosserp/cli.py`、`scripts/gen_samples.py`、`scripts/sample_vocab.py`、`samples/synthetic/expected/profit_expected.csv`、`tests/golden/profit_expected.csv`、`tests/golden/issues_expected.csv`、`tests/golden/test_golden.py`、`docs/eval-results/README.md`、相关任务文档和 `CHANGELOG.md`。
- 测试结果：SQLite 全量 `201 passed, 2 skipped`，覆盖率 `86.26%`；`tests/golden` SQLite `55 passed`；MySQL 8.4 和 PostgreSQL 18 golden 定向测试各 `30 passed`；`check-golden` 输出 `8/8 行完全一致、reference-only 12 行、异常 6/6 条一致`；故意把 profit 改大 0.01 的单测通过；样本生成器 `--check`、ruff、mypy、pre-commit 通过。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 偏离计划：当前合成数据只有 8 个可运行利润 SKU，因此 12 行明确标记 `reference-only`，没有伪装成运行结果；maken 的 20 个真实 SKU 仍按人工验收清单放在忽略目录中。
