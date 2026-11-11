# T19 对账补充规则：在途/待下期、多收费、拒付、部分退款、重复结算

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1.5 天 | T18 | `task/T19-recon-extra-rules` |

## 目标
把 T08 埋的「不算错但要提示」和「匹配上了但有问题」的场景都识别出来：在途订单不误报，多收费、拒付、部分退款、重复结算各有明确标记。

## 背景
- 实施方案 6.1（`NOT_IN_SETTLEMENT` 超过 GRACE_DAYS 才报，默认 14）、6.2 第 5 步。
- T08 场景表：多收费、在途/跨期（含 Shopify 未打款交易）、全额退款、部分退款、拒付。
- T14 候选码（`FEE_OVERCHARGE`、`SETTLEMENT_DELAYED`/待下期、`CHARGEBACK`、`PARTIAL_REFUND`、`DUPLICATE_SETTLEMENT`）**是否启用以 T17 定稿的 `IssueKind` 为准**：枚举里没有的码，本任务对应规则**不实现**，在 PR 里列出跳过了哪些。
- 下面所有阈值、口径都是建议值（推断），以 `docs/rules/recon-categories.md` 里 maken 的答复为准；没答复的用建议值并在 PR 里列出。

## 范围
规则都注册到 T18 的注册表，各有 id 和 version：
- `R10 not_in_settlement`：本店铺订单行在本期没被任何结算匹配，且 `order_date < as_of − grace_days` → `NOT_IN_SETTLEMENT`（`as_of` 默认 = 本期最后一天；`--as-of` 可覆盖）；`order_date ≥ as_of − grace_days` 的 → 若启用 `SETTLEMENT_DELAYED` 则开 info 级（不算未匹配），否则不开任何异常、只计入报告「待下期」数。**两者都不进匹配率分母**（分母只算结算行组）。Shopify `Payout Status` 为未打款的交易同样视为待下期（取值以 T11 vocab 为准）。
- `R11 fee_overcharge`（需 `FEE_OVERCHARGE` 启用）：已匹配组里 FBA 配送费/件 = |Σfba| ÷ qty，大于 `fee_reference` 中该内部 SKU 在订单日期有效的参考值 + 容差 → `FEE_OVERCHARGE`（warn，`counts_as_unmatched=False`，匹配仍算成功），detail 带实际、参考、差额、多收合计。容差默认 `0.00`（推断；绝对值还是百分比等 maken 在 T14 开放问题里答复）。没有参考值的 SKU 不检查、不报错。
  - 需要把 `fee_reference.csv` 导进库：新表 `fee_reference(id, store_id NULL, internal_sku String(64), fee_category String(32), currency String(3), expected_per_unit Money4, valid_from Date, valid_to Date NULL, import_batch_id)`（迁移 `000x_fee_reference`），并给 T12 通用映射器加 target `fee_reference` + `samples/synthetic/mappings/fee_reference.yaml`；`demo-import` 顺序里加上它（在 costs 之后）。
- `R12 chargeback`（需 `CHARGEBACK` 启用）：组内含拒付类交易行（Amazon/Shopify 的取值放 `recon/vocab.py`，T08 写的是合成取值，**真实取值待真实数据验证**）→ 匹配照常判定；另开 `CHARGEBACK`（warn）。利润口径不变（按退款类计入，见 T20）。
- `R13 partial_refund`（需 `PARTIAL_REFUND` 启用）：组内退款行 |Σ退款 principal| > 0 且 < Σ订单 principal → `PARTIAL_REFUND`（info）；不影响匹配，不得报 `QTY_MISMATCH`。
- `R14 duplicate_settlement`（需 `DUPLICATE_SETTLEMENT` 启用）：同一 `(order_id, sku)` 的订单类正向 principal 出现在**两个不同** `settlement.external_id` 里 → 在第二个结算的组上开 `DUPLICATE_SETTLEMENT`（error，`counts_as_unmatched=True`，该组不算匹配）。与导入阶段的 `DUPLICATE_ROW`（同一文件内原样重复行）区分清楚，测试覆盖两者不会同时对同一行报。
- 合成样本：如 T08 还没有「重复结算」场景，在 `scripts/gen_samples.py` 补一组（第二个 Amazon 结算文件里再出现一次某订单的 Order 行），更新 `EXPECTED.md`、`anomalies.json`、`summary.json`，并保持生成器的 ≤5% 未匹配自检通过。

## 不做
- 不做自动关闭异常、不做 AI 判断。
- 不改利润计算（T20）。

## 步骤
1. 先写测试：每条规则单测正反例；`tests/integration/test_recon_synthetic.py` 扩充为「anomalies.json 里每个场景都被识别，且没有多余的原因码」。
2. 迁移 + 映射 target + 规则。
3. `reconcile` 摘要输出加：待下期数、多收费合计（按币种）、拒付笔数。

## 涉及文件
`src/crosserp/recon/rules/*.py` `src/crosserp/recon/vocab.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_fee_reference.py` `src/crosserp/connectors/generic_mapped.py` `samples/synthetic/mappings/fee_reference.yaml` `scripts/gen_samples.py` `samples/synthetic/*`（重新生成） `src/crosserp/cli.py` `tests/unit/recon/*` `tests/integration/test_recon_synthetic.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/recon -q` | passed |
| `uv run pytest -m db -k recon -q`（三库） | passed；anomalies.json 每个场景命中 |
| `uv run python scripts/gen_samples.py --check` | 生成结果与仓库里的一致（可复现） |
| `uv run crosserp reconcile --period 2026-10 --as-of 2026-10-31` 与 `--as-of 2026-11-30` | 后者「待下期」变少、`NOT_IN_SETTLEMENT` 变多 |

## maken 人工验收清单
- [ ] `uv run crosserp reconcile --period 2026-10`，看「待下期」那一栏：10/25–10/31 的订单应该在这里，**不是**报错。
- [ ] `uv run crosserp issues list --kind FEE_OVERCHARGE`，打开 `samples/synthetic/fee_reference.csv` 对一下多收了多少。
- [ ] 回答 PR 里列出的口径问题（多收费容差、拒付是否单列）。

## 问题

## 完成记录

- 完成内容：新增 `R10` 待下期/超宽限期订单侧异常、`R11` 配送费参考和多收费提示、`R12` 拒付提示、`R13` 部分退款提示、`R14` 重复结算异常；Shopify pending 不进入匹配率分母；CLI 增加待下期、多收费和拒付统计；合成样本新增 1 个正常组以保持 120 组 / 114 匹配 / 95%。多收费采用绝对金额容差 0.00，拒付单列提示。
- 修改文件：`src/crosserp/recon/engine.py`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0006_fee_reference.py`、`src/crosserp/db/repo/imports.py`、通用映射连接器/导入器、`src/crosserp/cli.py`、原因码目录、`scripts/gen_samples.py`、合成样本、golden/集成/守卫测试及相关文档。
- 测试结果：`uv run python scripts/gen_samples.py --check` 通过；T19 单测/性质/合成集成定向测试通过；Amazon/Shopify golden `37 passed`；SQLite 全量 `192 passed, 2 skipped`，覆盖率 `85.92%`；MySQL 8.4 完整 db 标记测试 `94 passed, 3 skipped`；PostgreSQL 18 完整 db 标记测试 `93 passed, 4 skipped`；ruff、mypy、pre-commit 全部通过。
- 偏离计划：合成订单从 T08 的 120 行调整为 121 行，新增订单只用于保持 pending 排除分母后的 95% 指标；没有删除在途场景。`gh` 未安装，PR 通过 GitHub 网页创建。
