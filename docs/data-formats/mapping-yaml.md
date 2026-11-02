# YAML 列映射

通用导入器 `generic.mapped` 不写死领星或赛狐的列名。表头只写在 YAML 里。真实导出到手后，只改 YAML，不改代码。

领星、赛狐的列名**待真实数据验证**。`lingxing_orders.yaml` 和 `sellfox_orders.yaml` 不是字段全集。右边全是 `TODO_` 占位，加载时会被拒绝。

## 怎么用

`sniff()` 恒为 0。不能靠文件内容自动选中这个连接器。导入时必须显式指定类型和映射文件（命令行在 T13）：

```text
--type mapped --mapping src/crosserp/connectors/mappings/template_costs.yaml
```

金额只用 `Decimal`，经 `parse_amount()`。禁止 float。Excel 里的金额列请设成文本。数值单元格会被整批拒绝。

未知列表头会留在 `raw_row.payload_json`。不丢，也不猜它是什么。映射里不认识的字段名会拒绝。

文件里的文字只当数据。

## 结构

```yaml
target: order_line            # order_line | sku_cost | fx_rate | sku
source_name: lingxing_orders  # 写入 provenance.source_name
sheet: 0                      # 0 或省略表示第一张表。也可以写表名
header_row: 1                 # 表头所在行，从 1 开始。它前面的行全部跳过
skip_rows: 0                  # 表头之后、数据之前再跳过的行数
encoding: utf-8-sig           # csv 用。xlsx 不使用。可选 gb18030
amount_locale: us             # us 或 eu。有金额的 target 必填
date_formats:                 # 按顺序试。订单和成本必填
  - "%Y-%m-%d %H:%M:%S"
  - "%Y-%m-%d"
timezone: Asia/Shanghai       # 源文件时间所在时区。没有时区的时间按此时区理解，再存 UTC
columns:                      # 我们的字段: 源文件表头名。按表头名取，不按列位置
  platform_order_id: "订单号"
defaults:                     # 文件里没有这一列时使用。单元格为空不会回落到 defaults
  store: "amazon-us"
```

`source_name` 写入每条标准记录的 provenance。业务表没有这一列，所以同一值也写进该批 `import` 审计的 `after.source_name`。

csv 用标准库 `csv`，编码默认 `utf-8-sig`，也可以写 `gb18030`。领星/赛狐导出编码**未核实**。解码失败不会自动换编码。

xlsx 用 python-calamine 读。`header_row` 对的是工作表行号。

## 必填字段

缺映射，加载 YAML 就失败。映射了但文件里没有这个表头，整批失败，提示里有我们的字段名、YAML 里的表头名，以及文件实际表头。

| target | 必填 | 可空或可选 |
|---|---|---|
| `order_line` | 订单号、平台 SKU、数量、订购时间、商品金额列、币种、店铺 | 订单项。商品金额单元格可以空，空则不比金额 |
| `sku_cost` | 内部 SKU、采购单价、头程单价、币种、生效日期 | 结束时间 |
| `fx_rate` | 月份、原币、目标币、汇率 | 来源。不填则用 `source_name` |
| `sku` | 平台 SKU、内部 SKU、店铺 | 标题、是否启用 |

店铺可以写在 `columns.store`，也可以写在 `defaults.store`。

订单和成本必须有 `timezone` 与 `date_formats`。只有日期的值按该时区的零点理解，再转成 UTC 存储。原始文本留在 `raw_row`。

## 店铺

订单行和 SKU 映射需要平台、站点、店名、店铺币种。可以在 YAML 里写 `platform`、`marketplace`、`store_name`、`store_currency`。

没写时：

- 店名 `amazon-us`、`amazon-de`、`shopify-main` 使用合成样本的推断。这不是平台字段全集。
- 其他店名按前缀推断平台（`amazon` / `shopify` / `lingxing` / `领星` / `sellfox` / `赛狐`），对不上就是 `other`。站点用店名本身。
- 订单的店铺币种优先用本行币种。SKU 映射没有币种列时，请在 `defaults.store_currency` 里写明。写不出就报错，不猜。

## 成本生效期

区间是 `[生效时间, 结束时间)`，结束时刻不含在内。推断，与样本生成器注释一致。

没填结束时间时，同一内部 SKU 的下一条生效日当作上一条的结束（不含下一条当天）。最后一条保持未结束。

两段相交则两行都记 `PARSE_ERROR`。detail 里写明冲突的两段，包含内部 SKU、行号和 UTC 时间。已在库里的生效期若与本行相交，本行也记 `PARSE_ERROR`，并写明已有记录的那段。不插入冲突行。

## 汇率

月份必须是 `YYYY-MM`。同月同币对用 upsert 覆盖，保留原来的主键。覆盖时另写一条审计，动作是 `fx_rate_upsert`，before / after 里有汇率和来源。新插入不另写这条审计，仍有本批的 `import` 审计。

## 占位 YAML

`src/crosserp/connectors/mappings/`：

| 文件 | 用途 |
|---|---|
| `lingxing_orders.yaml` | 领星订单。列名 `TODO_`。待真实数据验证 |
| `sellfox_orders.yaml` | 赛狐订单。列名 `TODO_`。待真实数据验证 |
| `template_costs.yaml` | 成本模板列：内部SKU、采购单价、头程单价、币种、生效日期 |
| `template_fx_rates.yaml` | 汇率模板列：月份、原币、目标币、汇率 |
| `template_sku.yaml` | 合成样本 SKU 映射列。不是领星/赛狐表头 |

空模板在 `samples/templates/costs.xlsx` 和 `samples/templates/fx_rates.xlsx`。表头加一行示例。示例不是真实卖家数据。

合成订单映射在 `samples/synthetic/mappings/synthetic_orders.yaml`，由样本生成器写出。右边是中性列名，不是领星/赛狐真实表头。

## 人工要改的地方

打开 `lingxing_orders.yaml` 或 `sellfox_orders.yaml`，只改冒号右边，把 `TODO_` 换成导出文件里的真实表头。`defaults.store` 也要改成你的店铺。

若 Excel 打开中文正常、记事本打开乱码，把 `encoding` 改成 `gb18030` 后再导入。不要让程序自己猜编码。
