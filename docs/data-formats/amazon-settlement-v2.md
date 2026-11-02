# Amazon 结算报告 Flat File V2

连接器 id：`amazon.settlement_v2`。版本 `0.1.0`。只读 tab 分隔的 Flat File V2。不做 XML，不做旧版 Flat File，不调 SP-API。

## 来源

- 官方字段与金额格式：[Settlement Reports](https://developer-docs.amazon.com/sp-api/docs/report-type-values-settlement)。报告类型 `GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2`。制表符分隔。需要 Finance and Accounting 角色。官方写明欧洲站金额示例是 `95,00`，不是 `95.00`。
- 结算报告不能主动请求或预约，由亚马逊生成，只能用 `getReports` 查找。同一官方文档。本连接器不拉报告，只读已经下载的文件。
- 手动下载路径：Seller Central「Payments > All Statements > Download Flat File V2」。来源是[卖家论坛帖](https://sellercentral.amazon.com/seller-forums/discussions/t/6b82228c-034f-45d4-a4b1-859a6dd6f43d)，不是官方文档。

## 字段

列名来自官方列表。按表头名取列，不按位置。缺了下面「必需」列，整批失败，并列出缺哪几列。其余列缺失不失败，当作空。多出来的列留在 `raw_row`，并写 1 条 `PARSE_ERROR`（severity=`info`，说明「未知列已保留」）。不另设原因码。

| 列名 | 用途 | 状态 |
|---|---|---|
| `settlement-id` | 结算单外部单号 | 列名已核实。必需 |
| `settlement-start-date` | 期间开始 | 列名已核实。日期格式待真实数据验证 |
| `settlement-end-date` | 期间结束 | 列名已核实。日期格式待真实数据验证 |
| `deposit-date` | 打款日。空则不填 | 列名已核实。日期格式待真实数据验证 |
| `total-amount` | 汇总行总额 | 列名已核实。必需。格式待真实数据验证 |
| `currency` | 3 位大写币种 | 列名已核实。必需。小写或其他写法待真实数据验证 |
| `transaction-type` | 交易类型 | 列名已核实。必需。取值全集待真实数据验证 |
| `order-id` | 订单号 | 列名已核实 |
| `merchant-order-id` | 只留在原始行 | 列名已核实。本表没有对应标准列 |
| `adjustment-id` | 只留在原始行 | 列名已核实 |
| `shipment-id` | 只留在原始行 | 列名已核实 |
| `marketplace-name` | 站点。也用作店铺名 | 列名已核实。店名用法是推断，待真实数据验证 |
| `amount-type` | 费用分类的一半 | 列名已核实。必需。取值全集待真实数据验证 |
| `amount-description` | 费用分类的另一半 | 列名已核实。必需。取值全集待真实数据验证 |
| `amount` | 交易行金额 | 列名已核实。必需 |
| `fulfillment-id` | 只留在原始行 | 列名已核实 |
| `posted-date` | 没有 `posted-date-time` 时用作入账时间 | 列名已核实。优先顺序是推断 |
| `posted-date-time` | 入账时间。非空时不再改用 `posted-date` | 列名已核实。优先顺序是推断 |
| `order-item-code` | 订单项 | 列名已核实 |
| `merchant-order-item-id` | 只留在原始行 | 列名已核实 |
| `merchant-adjustment-item-id` | 只留在原始行 | 列名已核实 |
| `sku` | 平台 SKU | 列名已核实 |
| `quantity-purchased` | 数量。空则不填。只接受整数文本 | 列名已核实 |
| `promotion-id` | 只留在原始行 | 列名已核实 |

## 识别

`sniff` 用 UTF-8（去掉 BOM）读首行，按 tab 分割。同时有 `settlement-id`、`amount-type`、`amount-description`、`total-amount` 时分数是 0.95，否则是 0。

## 汇总行

推断，待真实数据验证：`transaction-type` 为空且 `total-amount` 非空的行是汇总行。它写成 `settlement`，不写成 `settlement_line`，也不加进交易金额合计。

同一文件可能有多个 `settlement-id`。按这个单号分组。这是推断。合成样本一个文件只有一张结算单。

两行汇总完全相同：第二行是 `DUPLICATE_ROW`，不建第二张结算单。两行汇总的单号相同但内容不同：不猜用哪一张，两行都记 `PARSE_ERROR`，这张单的明细也不写入结算表。原始行仍保留。

## 金额

每一行用 `locale_for(marketplace-name, currency)` 选 `us` 或 `eu`，再 `parse_amount()`。不按列位置，也不全局把逗号换成点。

当前规则：币种是 EUR，或站点 casefold 后落在 `amazon.de` / `amazon.fr` / `amazon.it` / `amazon.es` / `amazon.nl`，用欧洲格式。其他用美国格式。站点表待真实数据验证。英国站和其他币种没有真实文件，不提前加。

解析失败的那一行记 `PARSE_ERROR`，不写入结算明细。原始行保留。这一行算不出金额时，不再报 `SETTLEMENT_UNBALANCED`，因为差额不可靠。这是推断。

## 日期

`parse_amazon_date()` 把能识别的值转成 UTC。空字符串当作没有日期。无法识别则该行 `PARSE_ERROR`。

下面几种写法有测试。全部待真实数据验证。合成样本只输出前两种里的日期，以及 `YYYY-MM-DD HH:MM:SS UTC`：

- `2026-10-14`
- `2026-10-14 07:00:00 UTC`（后缀必须是大写 `UTC`）
- `14.10.2026`
- 带时区的 ISO-8601，例如 `2026-10-14T07:00:00Z`、`2026-10-14T09:00:00+02:00`

没有时区的时间文本不猜时区。只有日期、没有时间的，存成 UTC 当天 00:00。这也是推断。

## 费用分类

映射文件：`src/crosserp/connectors/amazon_settlement_v2/fee_map.yaml`。

初版只收录合成样本 `scripts/sample_vocab.py` 的 `KNOWN_FEE_PAIRS`。每条来源都是 `synthetic`，不是真实文件。

| amount-type | amount-description | fee_category | 来源 |
|---|---|---|---|
| `ItemPrice` | `Principal` | `principal` | 合成。待真实数据验证 |
| `ItemFees` | `Commission` | `commission` | 合成。待真实数据验证 |
| `ItemFees` | `FBAPerUnitFulfillmentFee` | `fba` | 合成。待真实数据验证 |

不在表里的组合：行仍入库，`fee_category=other`，另写 `UNKNOWN_FEE_TYPE`。detail 含原来的 `amount-type`、`amount-description` 和行号。不丢行，不猜分类。

合成样本没有仓储费、移除费、FBA 赔偿、促销。真实文件里如果有，应进未知费用。不要猜。

## 校验

- 每个 `settlement-id`：交易行 `amount` 之和（含文件里的重复行，不含汇总行）等于汇总行 `total-amount`。不等则 `SETTLEMENT_UNBALANCED`。detail 含 `total_amount`、`line_sum` 和 `diff`（明细合计减总额）。
- 文件里完全相同的两行：第二行 `DUPLICATE_ROW`。原始行保留，不写入 `settlement_line`。重复交易行的金额仍算进上面的总额校验，因为文件总额含这两行。
- 店铺按 `platform=amazon`、`marketplace=marketplace-name`、店名也用 `marketplace-name`、币种查找或创建。店名没有单独列。推断，待真实数据验证。

## 待真实数据验证

- 汇总行是不是「`transaction-type` 为空且 `total-amount` 非空」，以及它是不是总在明细前面。
- 一个文件会不会有多个 `settlement-id`。
- 日期的真实写法。上面列的格式只是解析器能读的范围，不是平台文档里的完整格式。
- `transaction-type`、`amount-type`、`amount-description` 的取值全集。
- `marketplace-name` 的真实写法，以及非 EUR 欧洲站用哪种小数格式。
- 币种列会不会出现小写或带空格。
- `posted-date` 和 `posted-date-time` 哪个为准，两者不一致时以谁为准。
- 没有单独店名列时，店铺名是否就是 `marketplace-name`。
- 仓储费、移除费、赔偿、促销等费用名。确认前不要写进 `fee_map.yaml`。
