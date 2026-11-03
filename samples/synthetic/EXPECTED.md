# 合成样本标准答案

种子 `20261109`。金额是合成值，不是真实卖家数据，也不是平台真实费率。
平台取值见 `scripts/sample_vocab.py`，一律「待真实数据验证」。
行号从 1 起，表头是第 1 行。

## 匹配率

- 定义：已匹配的订单类结算行组数 / 全部订单类结算行组数。Amazon 按 (order-id, sku) 分组。transaction-type 属于 Order/Refund/Chargeback（待真实数据验证）。Shopify 按 Order 分组，Type 属于 charge/refund/dispute（待真实数据验证）。未匹配原因码：NOT_IN_ERP、REFUND_WITHOUT_ORDER、QTY_MISMATCH、AMOUNT_MISMATCH、SKU_UNMAPPED。Shopify Net ≠ Amount − Fee 使用 AMOUNT_MISMATCH，计入未匹配组。amazon_us_unbalanced.tsv 不进入分母。非订单类行不进入分母。重复行不另计一组。
- 订单类结算行组数：120
- 已匹配：114
- 未匹配：6
- 预期匹配率：0.95（≥ 0.95）
- 未匹配占比：0.05（≤ 0.05）
- GRACE_DAYS：14

## 核对时不要误判

- 全额退款、部分退款、拒付应匹配成功。比较金额时只用 Order 的 Principal，不要把 Refund/Chargeback 的 Principal 轧差后再和 item_price 比。推断，与场景表一致。
- 同一订单多行的 quantity-purchased 重复填写同一数量。对账按订单项取一次。不要把费用行数量加总。推断。待真实数据验证。
- 部分退款的 Refund 行 quantity-purchased 为 0。Order 行数量与订单 qty 相同。不得报 QTY_MISMATCH。
- 10/25 与 10/31 的订单不在任何结算里。当前应标待下期，不是错。
- `FEE_OVERCHARGE?` 是候选原因码，确认前不要写进正式枚举。

## 场景

### normal

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：3, 4, 5
- 订单号：SYN-US-0001
- SKU：CUP-US-001
- 期望原因码：（匹配成功，无异常）
- 说明：Order 的 Principal、佣金、FBA 与订单表一致，应匹配成功。代表行，不是全部正常单。

### fee_overcharge

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：262, 263, 264
- 订单号：SYN-US-FEE
- SKU：CUP-US-001
- 期望原因码：FEE_OVERCHARGE?
- 说明：FBA 配送费 5.50 高于 fee_reference.csv 的 3.50/件。匹配仍成功。候选原因码，maken 确认前写 FEE_OVERCHARGE?。订单表第 108 行。

### in_transit

- 文件：`orders.csv`
- 行号：120
- 订单号：SYN-US-INTRANSIT
- SKU：CUP-US-001
- 期望原因码：NOT_IN_SETTLEMENT
- 说明：订单日期 2026-10-25，不在任何结算/打款文件。不算错：仅超过 GRACE_DAYS=14 后才报，否则标待下期。

### in_transit

- 文件：`orders.csv`
- 行号：121
- 订单号：SYN-DE-INTRANSIT
- SKU：PAD-DE-002
- 期望原因码：NOT_IN_SETTLEMENT
- 说明：订单日期 2026-10-31，不在任何结算/打款文件。不算错：仅超过 GRACE_DAYS=14 后才报，否则标待下期。

### in_transit

- 文件：`shopify_payout_2026-10-21.csv`
- 行号：6
- 订单号：SYN-SH-PENDING
- SKU：SH-TEE-001
- 期望原因码：NOT_IN_SETTLEMENT
- 说明：Payout Status=pending（待真实数据验证），当作未打款。行在打款导出里，但不算已结算。GRACE_DAYS 内标待下期，不报错。订单表第 115 行。

### refund

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：265, 266, 267, 268, 269
- 订单号：SYN-US-REFUND
- SKU：MUG-US-002
- 期望原因码：（匹配成功，无异常）
- 说明：同一订单有 Order 和 Refund，Refund 含退回的佣金。按订单号合并后匹配成功，利润里退款为负。不得因退款行把 Principal 轧差后报 AMOUNT_MISMATCH。订单表第 109 行。

### partial_refund

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：270, 271, 272, 273, 274
- 订单号：SYN-US-PARTIAL
- SKU：BAG-US-003
- 期望原因码：（匹配成功，无异常）
- 说明：Refund Principal 10.00 < Order Principal 60.00。Order 行 quantity-purchased 仍为 2，与订单 qty 相同。匹配成功，不得报 QTY_MISMATCH。订单表第 110 行。

### chargeback

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：278
- 订单号：SYN-US-CB
- SKU：CUP-US-001
- 期望原因码：（匹配成功，无异常）
- 说明：Amazon Chargeback 类交易（transaction-type 待真实数据验证）。匹配到原订单，按退款类计入利润。scenario=chargeback，便于以后单独分类。订单表第 111 行。

### chargeback

- 文件：`shopify_payout_2026-10-21.csv`
- 行号：8
- 订单号：SYN-SH-CB
- SKU：SH-TEE-001
- 期望原因码：（匹配成功，无异常）
- 说明：Shopify dispute 类交易（Type 待真实数据验证）。原 charge 在 shopify_payout_2026-10-07.csv 第 6 行。匹配到原订单，按退款类计入利润。scenario=chargeback。

### refund_without_order

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：297, 298
- 订单号：SYN-US-REFUND-NO-ORDER
- SKU：CUP-US-001
- 期望原因码：REFUND_WITHOUT_ORDER
- 说明：Refund 行的订单号不在 orders.csv。sku 在 sku_map.csv，所以不是 SKU_UNMAPPED。

### not_in_erp

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：294, 295, 296
- 订单号：SYN-US-NOT-IN-ERP
- SKU：CUP-US-001
- 期望原因码：NOT_IN_ERP
- 说明：Order 行的订单号不在 orders.csv。sku 在 sku_map.csv，所以不是 SKU_UNMAPPED。

### qty_mismatch

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：282, 283, 284
- 订单号：SYN-US-QTY
- SKU：MUG-US-002
- 期望原因码：QTY_MISMATCH
- 说明：结算 quantity-purchased=1，订单 qty=3。Principal 与 item_price 一致，只报数量不符。订单表第 116 行。

### amount_mismatch

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：285
- 订单号：SYN-US-AMT
- SKU：BAG-US-003
- 期望原因码：AMOUNT_MISMATCH
- 说明：Order Principal 22.00 ≠ 订单 item_price 25.00。数量一致。订单表第 117 行。

### sku_unmapped

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：288, 289, 290
- 订单号：SYN-US-UNMAPPED
- SKU：SYN-UNMAPPED
- 期望原因码：SKU_UNMAPPED
- 说明：结算 sku 不在 sku_map.csv。订单在 orders.csv 第 118 行。按实施方案 6.2 先查映射。期望 SKU_UNMAPPED。

### cost_missing

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：279, 280, 281
- 订单号：SYN-US-COST
- SKU：COST-GAP-US
- 期望原因码：COST_MISSING
- 说明：内部 SKU INT-COST-GAP 在 costs.csv 只有生效日期 2026-11-01。不覆盖订单日期 2026-10-06。对账匹配成功，利润计算时报缺成本。订单表第 112 行。

### fx_missing

- 文件：`amazon_de_2026-10-01_2026-10-14.tsv`
- 行号：39, 40, 41
- 订单号：SYN-DE-FX
- SKU：BOT-DE-001
- 期望原因码：FX_MISSING
- 说明：用 fx_rates_missing_eur.csv 代替 fx_rates.csv 时，DE 店铺 2026-10 没有 EUR→CNY。正常汇率表有该汇率。匹配成功，W3 利润计算才产生。金额原文含 95,00。订单表第 113 行。

### unknown_fee_type

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：299
- 订单号：（无）
- SKU：（无）
- 期望原因码：UNKNOWN_FEE_TYPE
- 说明：amount-description=SyntheticUnknownFee，不在 sample_vocab.KNOWN_FEE_PAIRS。transaction-type=other-transaction，非订单类，不进匹配率分母。不丢行。

### settlement_unbalanced

- 文件：`amazon_us_unbalanced.tsv`
- 行号：2
- 订单号：（无）
- SKU：（无）
- 期望原因码：SETTLEMENT_UNBALANCED
- 说明：汇总行 total-amount 6.00 ≠ 明细 amount 之和 5.00。该文件不进入匹配率分母。

### shopify_net_mismatch

- 文件：`shopify_payout_2026-10-21.csv`
- 行号：7
- 订单号：SYN-SH-NET
- SKU：SH-TEE-001
- 期望原因码：AMOUNT_MISMATCH
- 说明：Net 19.00 ≠ Amount 20.00 − Fee 0.40 = 19.60。订单仍在 orders.csv，但这条 AMOUNT_MISMATCH 计入未匹配组。订单表第 119 行。

### duplicate_row

- 文件：`amazon_us_2026-10-01_2026-10-14.tsv`
- 行号：6
- 订单号：SYN-US-0001
- SKU：CUP-US-001
- 期望原因码：DUPLICATE_ROW
- 说明：第 6 行与第 5 行完全相同。第二行是重复行。文件总额含这两行。匹配率不把重复行另计一组。

## 本样本没有的费用

不是全集。没有生成仓储费、移除费、FBA 赔偿、促销。真实文件里如果有，应进未知费用。不要猜。
