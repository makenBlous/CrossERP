# T08 合成样本生成器：120 单 + 结算/打款文件 + 故意埋的边界情况

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 1.5 天 | T03（只用 Money/Decimal，不需要数据库） | `task/T08-sample-generator` |

## 目标
`scripts/gen_samples.py` 用固定种子生成一套「已知正确答案」的假数据，后面所有导入、对账、利润测试都拿它做标准答案。真实数据到位前，这是唯一的测试基准。

## 背景
- 实施方案 5.6、8 W1 第 7 条（120 条订单、2 个 Amazon V2 结算、2 个 Shopify 打款、成本表、汇率表、SKU 标题含中文和 emoji、EXPECTED.md 列 6 类异常）。
- Amazon V2 字段（官方）：https://developer-docs.amazon/sp-api/docs/report-type-values-settlement
- Shopify 打款基础列（官方）：https://help.shopify.com/en/manual/payments/shopify-payments/payouts/view-details
- **重要**：`transaction-type`、`amount-type`、`amount-description` 的真实取值全集、Shopify `Type`/`Payout Status` 的取值，都「待真实数据验证」。生成器把这些取值集中写在 `scripts/sample_vocab.py`，每个值旁注明「待真实数据验证」，以后拿到真实文件只改这一个文件。
- 本任务把实施方案的「6 类异常」扩展为下面的场景表（扩展属任务拆分决定，推断；maken 可删减）。

## 范围
生成到 `samples/synthetic/`（提交进仓库）：
| 文件 | 内容 |
|---|---|
| `orders.csv` | 120 条订单行（中性列名：`order_id,order_item_id,store,platform_sku,qty,order_date,item_price,currency`），供 T12 映射导入 |
| `mappings/synthetic_orders.yaml` | 上面 orders.csv 的列映射 |
| `costs.csv` + `costs.xlsx` | 内部SKU、采购单价、头程单价、币种、生效日期（5.5 模板列）；至少 1 个 SKU 有两段生效期 |
| `fx_rates.csv` + `fx_rates.xlsx` | 月份、原币、目标币、汇率（USD→CNY、EUR→CNY 的 2026-10，数值为合成值，不是真实汇率） |
| `fx_rates_missing_eur.csv` | 同上但删掉 EUR→CNY，专门给 `FX_MISSING` 测试用 |
| `sku_map.csv` | 店铺、平台SKU、内部SKU、标题（标题含中文和 emoji，如「保温杯 🍵 黑色 500ml」） |
| `fee_reference.csv` | 每个 SKU 的「应收 FBA 配送费/件」（合成参考值，不是亚马逊真实费率），用于检测多收费 |
| `amazon_us_2026-10-01_2026-10-14.tsv` | Amazon.com，USD，US 小数格式，tab 分隔，V2 全部 24 列，第一行为汇总行 |
| `amazon_de_2026-10-01_2026-10-14.tsv` | Amazon.de，EUR，**EU 小数格式（`95,00`）** |
| `amazon_us_unbalanced.tsv` | 小文件：行合计 ≠ total-amount |
| `shopify_payout_2026-10-07.csv`、`shopify_payout_2026-10-21.csv` | 11 个官方基础列 |
| `EXPECTED.md` | 人看的标准答案：每个场景在哪个文件第几行、应产生什么原因码 |
| `expected/anomalies.json` | 机器读的同一份答案：`[{scenario, file, row_nos, order_id, sku, expected_issue_kind, note}]` |
| `expected/summary.json` | 每个文件的数据行数、每个 settlement 的 total、预期匹配率、订单类结算行组数 |

### 必须埋入的场景（每类至少 1 组，写进 anomalies.json）
| 场景 | 怎么造 | 期望结果（原因码见实施方案 6.1） |
|---|---|---|
| 正常 | 大部分订单：Order 行（Principal + 佣金 + FBA 费）与订单表一致 | 匹配成功 |
| **多收费 fee overcharge** | 某订单的 FBA 配送费比 `fee_reference.csv` 高 | 匹配成功 + 标记 `FEE_OVERCHARGE`（候选新原因码，见 T14；在 maken 确认前，anomalies.json 里 `expected_issue_kind` 写 `FEE_OVERCHARGE?`） |
| **在途 / 跨期 in-transit timing** | 10/25–10/31 的订单不出现在任何结算里；另 1 笔 Shopify 交易 `Payout Status` 为未打款状态 | 不算错：`NOT_IN_SETTLEMENT` 仅在超过 GRACE_DAYS（默认 14）后才报，否则「待下期」 |
| **全额退款 refund** | 同一订单在结算里有 Order 行 + Refund 行（含退回的佣金） | 按订单号合并后匹配成功，利润里退款为负 |
| **部分退款 partial refund** | Refund 金额 < Principal，数量不变 | 匹配成功；利润按实际退款额计；不得报 `QTY_MISMATCH` |
| **拒付 chargeback** | Amazon 侧一笔 Chargeback 类交易；Shopify 侧一笔 dispute 类交易（取值待真实数据验证） | 匹配到原订单，按退款类计入利润；anomalies.json 标注 `chargeback` 便于以后单独分类 |
| 无订单的退款 | Refund 行的订单号不在 orders.csv | `REFUND_WITHOUT_ORDER` |
| 订单表没有 | Order 行的订单号不在 orders.csv | `NOT_IN_ERP` |
| 数量不符 | 结算 quantity-purchased ≠ 订单 qty | `QTY_MISMATCH` |
| 金额不符 | Principal ≠ 订单 item_price | `AMOUNT_MISMATCH` |
| SKU 未映射 | 结算里的 sku 不在 sku_map.csv | `SKU_UNMAPPED` |
| 缺成本 | 某内部 SKU 在 costs.csv 里没有覆盖订单日期的生效期 | `COST_MISSING` |
| 缺汇率 | 用 `fx_rates_missing_eur.csv` 代替正常汇率表时，DE 店铺 2026-10 无 EUR→CNY | `FX_MISSING`（W3 利润计算时产生） |
| 未知费用类型 | 一行 amount-description 不在 fee_map 里 | `UNKNOWN_FEE_TYPE` |
| 结算不平 | `amazon_us_unbalanced.tsv` | `SETTLEMENT_UNBALANCED` |
| Shopify 净额不符 | 一行 `Net ≠ Amount − Fee` | `AMOUNT_MISMATCH` |
| 重复行 | 某一行原样出现两次 | `DUPLICATE_ROW` |

约束：导致「未匹配」的场景（NOT_IN_ERP、REFUND_WITHOUT_ORDER、QTY_MISMATCH、AMOUNT_MISMATCH、SKU_UNMAPPED）合计不超过订单类结算行组数的 5%，让指标 2（匹配率 ≥95%）在合成样本上可达；生成器结束时自检并打印预期匹配率。

## 不做
- 不写导入器、对账器（T09–T13、W3）。不使用任何真实卖家数据或真实亚马逊费率。

## 步骤
1. `scripts/sample_vocab.py`：集中定义取值（transaction-type、amount-type/description、Shopify Type/Payout Status、marketplace-name），全部注「待真实数据验证」。
2. `scripts/gen_samples.py`：`random.Random(20261109)` 固定种子；所有金额用 `Decimal` 生成并按格式输出（US：`1234.56`；EU：`1234,56`，不输出千分位，推断真实文件也不带，待验证）；Typer 或 argparse，`--out samples/synthetic`。
3. 先生成「干净」数据，再按场景表逐个注入，注入时同时写 anomalies.json，保证答案与数据同源。
4. 每个 Amazon 文件：汇总行的 total-amount = 其余所有行 amount 之和（unbalanced 文件除外）。
5. xlsx 用 openpyxl 写；csv/tsv 用 `newline=""`、UTF-8（无 BOM），行尾 `\n`。
6. 测试 `tests/unit/test_gen_samples.py`：
   - 生成到 `tmp_path` 两次，所有 csv/tsv/json 的 sha256 相同（确定性）；xlsx 比较单元格内容相同；
   - orders.csv 恰好 120 行；Amazon 文件 24 列；Shopify 文件含 11 个基础列；
   - 平衡文件 Σamount == total-amount；unbalanced 文件不等；
   - anomalies.json 覆盖场景表的每一类；预期匹配率 ≥ 0.95。
7. 运行生成器，把 `samples/synthetic/` 提交；写 `samples/synthetic/README.md`（如何重新生成）。

## 涉及文件
`scripts/gen_samples.py` `scripts/sample_vocab.py` `samples/synthetic/**` `tests/unit/test_gen_samples.py` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run python scripts/gen_samples.py --out samples/synthetic` | 打印各文件行数和「预期匹配率 ≥95%」 |
| 再运行一次后 `git status --porcelain samples/synthetic` | csv/tsv/json 无变化（xlsx 如有元数据变化需在 PR 说明） |
| `uv run pytest tests/unit/test_gen_samples.py -q` | passed |

## maken 人工验收清单
- [ ] 用 Excel 打开 `samples/synthetic/amazon_de_*.tsv`（数据 → 从文本导入，分隔符选 Tab），能看到金额是 `95,00` 这种逗号格式。
- [ ] 打开 `EXPECTED.md`，挑 3 个场景，按里面写的文件名和行号去文件里找到对应行，确认真的「埋」了问题。
- [ ] 打开 `sku_map.csv`，标题里有中文和 emoji 且不乱码。
- [ ] 读一遍场景表，告诉代理：有没有你实际业务里常见、但这里没有的情况（例如 FBA 赔偿、仓储费、移除费）。

## 问题

没有停工项。平台取值没有真实文件，已放进 `scripts/sample_vocab.py` 并注明「待真实数据验证」。

推断，供 W3 确认，不阻塞本任务：

- 全额退款 / 部分退款 / 拒付要匹配成功。比较金额时只用 Order 的 Principal，不要把 Refund / Chargeback 轧差后再和 `item_price` 比。否则与场景表冲突。
- 同一订单多行的 `quantity-purchased` 重复填写同一数量。对账应按订单项取一次。
- Shopify `Net ≠ Amount − Fee` 使用 `AMOUNT_MISMATCH`，并计入未匹配组。因此未匹配恰好 6 组，匹配率恰好 0.95。再加未匹配组就会跌破 95%，除非同时增加已匹配组。
- `amazon_us_unbalanced.tsv` 不进入匹配率分母。它只用于 `SETTLEMENT_UNBALANCED`。
- 没有生成仓储费、移除费、FBA 赔偿、促销。不是费用全集。

## 完成记录

当前分支 `main`（按本次指令提交到当前分支，未另开 `task/T08-sample-generator`）。未推送。未把状态改成 done。未改 `docs/tasks/README.md`。

2026-11-02 在本 worktree 实际运行。解释器 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`，Python 3.14.10。未使用 `uv run`。`PYTHONPATH` 指向本 worktree 的 `src`。

| 命令 | 结果 |
|---|---|
| `python scripts/gen_samples.py --out samples/synthetic` | 退出码 0。`orders.csv: 120 数据行`；`amazon_us_2026-10-01_2026-10-14.tsv: 295 数据行 total=3088.16`；`amazon_de_2026-10-01_2026-10-14.tsv: 40 数据行 total=571,18`；`amazon_us_unbalanced.tsv: 4 数据行 total=6.00 balanced=false`；两份 Shopify 打款 5 行 / 7 行。末行 `预期匹配率 ≥95%：实际 0.95，订单类结算行组 120，已匹配 114，未匹配 6` |
| 再运行一次后 `git status --porcelain samples/synthetic` | 无输出。csv/tsv/json/xlsx 都无变化。两次 xlsx sha256 也相同：`costs.xlsx` `7756fba528b099fb5d7065332a82d056a834d0aa25c5c9c02c8e5009dd16ab1c`，`fx_rates.xlsx` `255b01111ab886f67784974cd8e6c62fb65dfefd76c5c04604ed518fc9774bcf` |
| `python -m pytest tests/unit/test_gen_samples.py -q` | 退出码 0。`9 passed in 0.75s` |
| `python -m pytest -q` | 退出码 0。`33 passed in 1.21s` |
| `python -m ruff format --check .` | 退出码 0。`25 files already formatted` |
| `python -m ruff check .` | 退出码 0。`All checks passed!` |
| `python -m mypy` | 退出码 0。`Success: no issues found in 13 source files` |

预期匹配率 `0.95`。未匹配占比 `0.05`。金额只用 `Decimal`。`scripts/` 中没有 `float()` 调用。
