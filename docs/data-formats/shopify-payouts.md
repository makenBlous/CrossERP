'## 状态与关系

- **状态：已实现连接器文档；平台字段部分待真实数据验证**。代码位于 `src/crosserp/connectors/shopify_payouts/`；实体和动作以 [08](../design/08-后端模块与API设计.md) 及附件为准。
- 金额使用确定性 Decimal/万分位规则，原始列保留，未知字段不丢弃。

'# Shopify Payments 打款 CSV

连接器 id：`shopify.payouts`。只读本地 CSV，不调 Shopify API。

## 来源

- 官方基础列：[查看打款详情](https://help.shopify.com/en/manual/payments/shopify-payments/payouts/view-details)。后台 Finance > Payouts 导出，CSV 经邮件发送。
- 可选列来自第三方说明：[storepaperwork 指南](https://storepaperwork.com/guides/shopify-payments-transactions-export-columns-explained/)。非官方。全部「待真实数据验证」。

## 列

必须有这 11 个基础列，缺任何一个整批失败，并列出缺的列名：

`Transaction Date`、`Type`、`Order`、`Card Brand`、`Card Source`、`Payout Status`、`Payout Date`、`Available On`、`Amount`、`Fee`、`Net`。

可选列缺失不报错。存在则原样留在 `raw_row`，不猜测含义：

`Checkout`、`Payment Method Name`、`Presentment Amount`、`Presentment Currency`、`Currency`、`Payout ID`。

其他未知列也留在 `raw_row`。不丢、不改名、不映射到 SKU。官方基础列没有 SKU，也没有数量。

按表头名取值，不按列位置。表头会去掉首尾空白。重复列名或空列名整批失败。

识别：表头同时含 `Payout Date`、`Amount`、`Fee`、`Net`、`Type` 时 `sniff()` 为 0.9，否则为 0。分隔符按逗号 CSV。Shopify 是否永远用逗号，「待真实数据验证」。

## 分组

有 `Payout ID` 列时按它分组。没有则按 `Payout Date` 的原文分组。这是推断，待真实数据验证。

每组一个 `settlement`。`total` 是该组成功解析行的 `ΣNet`。文件没有打款总额列，不编造。故意写错的 `Net` 仍按原文加进总额。

外部单号：

- 有非空 `Payout ID`：用该值。超过 64 个字符整批失败，不截断。
- `Payout ID` 列存在但单元格为空：`payout-id:missing`。不并入其他 ID。
- 没有该列、`Payout Date` 非空：`payout-date:` 加日期原文。
- 没有该列、`Payout Date` 为空：`payout-date:missing`。

同一平台的 `external_id` 全局唯一。没有 `Payout ID` 时，两份文件如果打款日相同，后一份会整批失败。要不要把店铺或文件名放进外部单号，需要 maken 决定。

## 金额和币种

明细 `amount` 是该行 `Net`。`Amount` 和 `Fee` 留在 `raw_row`。这样各组明细之和等于 `settlement.total`。

`Net` 不等于 `Amount − Fee` 时，行仍按原文 `Net` 入库，并写一条 `AMOUNT_MISMATCH`。detail 含 `amount`、`fee`、`net`、`expected_net`、`diff`，都是字符串，不用 float。差额是 `Net − (Amount − Fee)`。不改原文。

默认按 US 小数格式解析。这是「待真实数据验证」。某个金额出现逗号小数时，按该行币种用 `locale_for(None, currency)` 选格式。EUR 会走欧式。USD 仍走 US，解析失败则该行 `PARSE_ERROR`，不改成欧式。

币种：有 `Currency` 列且该组只有一个非空值，用它。空单元格沿用该组唯一非空币种。没有列、或整组为空时，用 `ColumnMapping.defaults["currency"]`。这是给 T13 的 `--currency` 和店铺默认币种留的入口。连接器不查库。都没有则整批失败，提示用 `--currency` 或先设置店铺默认币种。同一组多种币种，或一个文件多种币种，整批失败，不猜测拆店。

## 日期

`Transaction Date` 必须带时区，转成 UTC 写入 `posted_at`。合成样本形态是 `2026-10-01 10:15:00 -0400`。其他形态「待真实数据验证」。没有时区的交易时间不猜测，该行 `PARSE_ERROR`。

`Payout Date` 只有日期时，推断为 UTC 零点，写入 `deposit_date`。待真实数据验证。空的 `Payout Date` 不把 `Available On` 当成打款日。`deposit_date` 为空。

`period_start` / `period_end` 是该组成功行的交易时间最小和最大值。

## Type 和状态

映射在 `src/crosserp/connectors/shopify_payouts/type_map.yaml`。已知取值忽略大小写。未知 `Type` 原样写入 `transaction_type`，并写 `UNKNOWN_FEE_TYPE`（severity=`warn`）。不丢行，不猜分类。

| 原文 Type | transaction_type | 来源 |
|---|---|---|
| `charge` | `charge` | 合成样本。待真实数据验证 |
| `refund` | `refund` | 合成样本。待真实数据验证 |
| `dispute` | `chargeback` | 合成样本。T11 要求入库为 chargeback 类。待真实数据验证 |
| `adjustment` | `adjustment` | 只出现在任务说明的例子里。合成样本没有。待真实数据验证 |

`amount_type` 保存去掉首尾空白后的原文 `Type`。

`Payout Status` 非已打款的行照常导入。合成样本把 `paid` 当作已打款、`pending` 当作未打款，都「待真实数据验证」。`settlement_line` 没有状态列。状态写在 `amount_description`，格式 `payout_status=<原文>`。这是推断。W3 也可回读 `raw_row` 的 `Payout Status`。若要单独列，需要 maken 决定是否改表。

本导入器不报 `NOT_IN_SETTLEMENT`，也不因 `dispute` 写 `CHARGEBACK`。那是 W3 对账。

## 店铺

文件没有店铺列。未传入时 `marketplace=shopify`、`store_name=Shopify`。推断。T13 可通过 `mapping.defaults` 的 `marketplace`、`store_name`、`currency` 覆盖。

## 待真实数据验证

- 导出是否永远是逗号 CSV、UTF-8。
- `Type`、`Payout Status` 的取值全集，以及大小写。
- `Payout ID`、`Currency` 和其他可选列是否真的出现，以及 `Payout ID` 的长度。
- `Transaction Date`、`Payout Date` 的真实格式和时区。
- 金额是否永远是 US 格式。
- 空 `Payout Date` 的行是否应单独成组。
