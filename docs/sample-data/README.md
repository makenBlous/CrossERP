# 真实样本数据准备说明（给 maken）

合成样本（`samples/synthetic/`，T08 生成）能证明代码「按我们的理解」是对的；**真实文件才能证明我们的理解是对的**。实施方案里很多格式细节标着「待真实数据验证」，都要靠这里的文件来确认。

## 1. 放在哪里
- 放到 `samples/real_anonymized/`（这个目录在 `.gitignore` 里，**不会被提交到 GitHub**）。
- 提交前用 `git status` 确认这个目录里的文件没有出现在列表里。
- 文件名建议：`<来源>_<店铺简称>_<期间>.<扩展名>`，例如 `amazon_us_2026-10a.tsv`、`shopify_main_2026-10.csv`、`lingxing_orders_2026-10.xlsx`。

## 2. 需要准备哪些文件
| # | 文件 | 从哪里下载 | 份数 | 用来验证什么 |
|---|---|---|---|---|
| 1 | Amazon 结算报告 Flat File V2（.txt/.tsv，tab 分隔） | Seller Central「Payments > All Statements > Download Flat File V2」（路径来自卖家论坛帖，非官方文档：https://sellercentral.amazon.com/seller-forums/discussions/t/6b82228c-034f-45d4-a4b1-859a6dd6f43d ） | 至少 2 期；**如果有欧洲站，另加 1 期欧洲站** | 汇总行结构、日期格式、`transaction-type` / `amount-type` / `amount-description` 全部取值、EU 小数格式 |
| 2 | Shopify Payments 打款交易 CSV | Shopify 后台 Finance > Payouts 导出（CSV 会发到邮箱，见 https://help.shopify.com/en/manual/payments/shopify-payments/payouts/view-details ） | 1–2 次打款，最好含 1 笔退款 | 真实表头（有没有 Payout ID / Currency 列）、`Type` 和 `Payout Status` 的取值 |
| 3 | 领星或赛狐的订单导出 | 领星/赛狐后台订单列表导出（xlsx 或 csv） | 与第 1 项**同一期间** | 真实表头 → 填进 `mappings/lingxing_orders.yaml` / `sellfox_orders.yaml`；编码 |
| 4 | 成本表 | 自己整理，或用 `samples/templates/costs.xlsx` 模板 | 1 份 | 内部 SKU、采购单价、头程单价、币种、生效日期 |
| 5 | SKU 映射表 | 领星/赛狐的 MSKU ↔ 本地 SKU 导出，或自己整理 | 1 份 | 平台 SKU 和内部 SKU 的对应 |
| 6 | 月汇率表 | 自己填（用你们财务实际记账用的汇率） | 1 份 | 月份、原币、目标币、汇率 |
| 7（可选） | 领星/赛狐的利润报表导出 | 后台利润报表 | 同期 1 份 | 和我们算的利润对比，找口径差异 |

最小可用组合：**第 1、3、4、5、6 项**（Amazon 一个店铺一个月）。

## 3. 怎么脱敏（每个文件都要做）
| 字段 | 处理方法 |
|---|---|
| 买家姓名、地址、电话、邮箱 | **整列删除** |
| 订单号 | 保留格式，替换数字，例如 `113-1234567-7654321` → `113-0000001-0000001`；**同一个订单在所有文件里替换成同一个新号**（否则对不上） |
| SKU / ASIN | 可以保留；如果敏感，用同样的「一一替换」方式，所有文件保持一致 |
| 商品标题 | 可以改成大概品类（如「保温杯 500ml」），但保留一两条带中文/emoji 的 |
| 金额 | **不要改**（改了就没法验证）；如果一定要改，所有文件按同一个系数等比例缩放，并在说明里写系数 |
| 店铺名、卖家 ID、settlement-id | 替换为假值，同一个值在所有文件里替换一致 |
| 银行账号（如有） | 删除 |

建议：用 Excel 的「查找替换」或让代理写一个本地脱敏脚本 `scripts/anonymize.py`（数据只在你电脑上处理）。**不要把未脱敏文件发给任何在线 AI 或网盘。**

脱敏后自查：用记事本打开每个文件，搜索 `@`（邮箱）、`+86`/`+1`（电话）、你的店铺名，确认搜不到。

## 4. 手算标准答案的格式（golden file）
实施方案指标 3：maken 用 Excel 手算 20 个 SKU 的利润，自动测试要求**逐分相等**。请按下面格式整理，存为 UTF-8 CSV，放 `samples/real_anonymized/expected/`。

### 4.1 `profit_expected.csv`（每个 SKU 一行，共 20 行）
| 列名 | 含义 | 示例 |
|---|---|---|
| `period` | 月份 | `2026-10` |
| `store` | 店铺简称（与文件名一致） | `amazon-us` |
| `internal_sku` | 内部 SKU | `CUP-500-BK` |
| `currency` | 结算币种 | `USD` |
| `qty_sold` | 销售数量 | `37` |
| `qty_refunded` | 退货数量 | `2` |
| `revenue` | 销售收入（商品价 + 买家付的运费），正数 | `1108.63` |
| `promotion` | 促销，负数 | `-25.00` |
| `platform_fees` | 平台费用合计（佣金 + FBA 配送费等），负数 | `-412.80` |
| `refunds` | 退款合计（含退回的费用），负数 | `-59.90` |
| `cogs` | 商品成本 = 数量 × 采购单价，正数 | `333.00` |
| `freight` | 头程 = 数量 × 头程单价，正数 | `55.50` |
| `ads` | 广告费，正数；v0.1 不含广告则填 `n/a` | `n/a` |
| `profit` | 利润（结算币种）= revenue + promotion + platform_fees + refunds − cogs − freight − ads | `222.43` |
| `fx_rate` | 当月汇率（结算币种 → CNY） | `7.10000000` |
| `profit_cny` | 人民币利润 | `1579.25` |
| `note` | 计算时的特殊处理说明 | `一笔部分退款 10.00` |

规则：
- 金额保留 2 位小数，用 `.` 作小数点，不写千分位、不写货币符号。
- 四舍五入只在最后一步（`profit`、`profit_cny`），用「四舍五入」（ROUND_HALF_UP），不要每一步都四舍五入。Excel 里中间列不要设置「显示 2 位」后又引用显示值。
- 退货数量是否回库（影响 cogs）：实施方案标为「待真实数据验证」，请在 `note` 写你的做法。
- 上面的示例数字只是格式示例，不是真实数据。

### 4.2 `issues_expected.csv`（你知道「有问题」的单子）
| 列名 | 含义 |
|---|---|
| `source_file` | 文件名 |
| `row_no` | 文件里第几行（表头算第 1 行） |
| `order_id` | 订单号（脱敏后） |
| `sku` | 平台 SKU |
| `expected_kind` | 你认为的原因：用 `docs/rules/recon-categories.md` 里的原因码；不确定就写 `UNKNOWN` |
| `note` | 人话说明，例如「这单 9 月下单、11 月才结算」 |

### 4.3 `settlement_expected.csv`（每个结算/打款一行）
`source_file, settlement_id, currency, total_amount, line_count`——`total_amount` 直接抄后台显示的结算总额，用来核对我们的「Σ明细 = 总额」校验。

## 5. 交给代理时怎么说
把文件放好后，对代理说：「`samples/real_anonymized/` 里有真实脱敏文件和 expected/ 标准答案，按 T13 的步骤试导入，把所有报错和未识别的列/费用类型整理成一张表给我，不要改 golden 期望值。」
