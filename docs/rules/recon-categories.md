# 对账异常分类

状态：草案，待 maken 确认。本文只定分类，不实现对账，也不改 `IssueKind`。
人话模板的机器可读稿在 `src/crosserp/issues/catalog_draft.yaml`。W3 的 issues 模块再读它。
事实来源：实施方案第 6.1、6.2、6.5 节；`samples/synthetic/expected/anomalies.json`；`samples/synthetic/EXPECTED.md`。
查询日期：2026-11-02。

没核实的写「未核实」。格式没拿真实文件对过的写「待真实数据验证」。从现有规则推出来的写「推断」。

## 1. 范围

v0.1 只对照这两边：

- 订单表：合成样本列是 `order_id`、`order_item_id`、`store`、`platform_sku`、`qty`、`order_date`、`item_price`、`currency`。这是本项目的中性列，不是领星或赛狐的真实表头。
- 结算：Amazon Flat File V2 的 24 个列名已在实施方案 5.1 核实。Shopify 官方基础列已在实施方案 5.2 核实：`Transaction Date`、`Type`、`Order`、`Card Brand`、`Card Source`、`Payout Status`、`Payout Date`、`Available On`、`Amount`、`Fee`、`Net`。

v0.1 没有银行流水。不设「缺银行流水」「银行参考号不符」这类结果。合成样本也没有这些字段。

候选原因码在 maken 确认前不得写入 `IssueKind`。确认前，合成样本里 `expected_issue_kind` 为空或写着 `FEE_OVERCHARGE?` 的场景，正式输出仍不得使用候选码。

## 2. 借鉴来源

只借鉴思路。不复制代码，不复制原文。两个仓库的实现和评测数字都「未核实」。本文没有引用它们的评测数字。

- [Varun-AI-Robotics/ledgerpilot-ai](https://github.com/Varun-AI-Robotics/ledgerpilot-ai)。2026-11-02 读了 README，并查了 GitHub API。API 的 `license` 为空，与任务文件「未显示许可证」一致。许可证正文未审。实现未核实。不得复制其代码。
- [Aoun-source/ledgerpilot-ai](https://github.com/Aoun-source/ledgerpilot-ai)。2026-11-02 读了 README，并查了 GitHub API。任务文件写该仓为 MIT；API 的 `spdx_id` 也是 MIT。许可证正文未审，不把这次查询当成法律意见。实现未核实。

从第一个仓库只取这几条思路，名字是它 README 里的结果类，不是我们的枚举：

- 对上与对不上由确定规则判定。模型只解释原因，并建议下一步。
- 费用与预期不一致、结算偏晚、同一笔收款出现两次，值得分开看。
- 可以有「只对上一部分」的状态。它的部分对账包含银行流水。我们没有银行流水，不能照搬那个定义。`partial` 的定义见第 4 节，是推断，待确认。

从第二个仓库只取这几条思路：

- 读不出或缺失的值交给人，不猜测，不补一个数。
- 金额只由代码算。
- 模型可以建议更严的处理，不能把规则放宽，也不能把异常关掉。
- 需要人点头的动作，人确认之前不做。

## 3. 共用判定

这些规则同时约束下面每一条原因码。

- 金额用 `Decimal` 比较。比较时不四舍五入。只在最终展示时保留到分。
- 订单类结算行，Amazon 按 `order-id` + `sku` 分组。`transaction-type` 属于 `Order` / `Refund` / `Chargeback`。这三个取值待真实数据验证，不是全集。
- Shopify 按 `Order` 分组，不按 SKU。官方基础列没有 SKU。样本里每个 Shopify 订单只有一个 SKU。一单多 SKU：样本未覆盖。不要编造 Shopify 的 SKU 列。
- `transaction-type` 或 `Type` 的取值全集待真实数据验证。不认识的组合不丢行，走 `UNKNOWN_FEE_TYPE`。
- 数量只从收款行取一次。Amazon 用 `transaction-type=Order` 的 `quantity-purchased`，同一 `order-item-code` 不把费用行加总。Refund 行的数量不参与这次比较。这是样本答案里的推断，待真实数据验证。
- 货款只加收款行的 Principal。Amazon：`transaction-type=Order` 且 `amount-description=Principal` 的 `amount`。不要把 Refund、Chargeback 的 Principal 轧进去再和 `item_price` 比。`amount-description` 的取值待真实数据验证。
- 样本里的 Amazon 费用是负数，货款是正数。和参考费率比时用费用绝对值。
- 实施方案 6.2 写了 `normalize(sku)`，没有定义怎么规范化。推断：只去掉首尾空白，不改大小写。待 maken 确认。不要编造平台 SKU 的大小写规则。
- 订单索引窗口是对账期间前后 60 天。这是实施方案 6.2 的规则，不是平台字段。
- `GRACE_DAYS` 默认 14，可配置。合成样本是 14。
- `period_end` 的取法，实施方案写了这个名字，没有写它是自然月月末还是文件里的 `settlement-end-date`。推断：对账命令按 `YYYY-MM` 跑，`period_end` 是该月最后一天。待 maken 确认。现有在途样本在两种取法下都不会报错，所以样本不能区分这两种取法。
- 一条异常的 `status` 初始是 `open`。v0.1 不提供关闭、忽略或解释落库。那些状态是以后的网页流程，不是本文件要实现的。

判定顺序，避免一条单子报一串互相打架的码：

1. 导入阶段可以单独产生 `PARSE_ERROR`、`DUPLICATE_ROW`、`UNKNOWN_FEE_TYPE`、`SETTLEMENT_UNBALANCED`。它们不替代后面的订单匹配，除非下面另有说明。
2. 组内 SKU 不在映射表：只报 `SKU_UNMAPPED`，不再报这组的 `NOT_IN_ERP`、`QTY_MISMATCH`、`AMOUNT_MISMATCH`。
3. 映射表有，订单表没有：组内行全是退款时报 `REFUND_WITHOUT_ORDER`，否则报 `NOT_IN_ERP`。
4. 数量不一致：只报 `QTY_MISMATCH`，不再比货款。
5. 币种不一致：只报 `CURRENCY_MISMATCH`，不报 `AMOUNT_MISMATCH`。这是推断。样本未覆盖。
6. 货款不一致：报 `AMOUNT_MISMATCH`，不写 `matched`。
7. 否则写 `matched`。利润阶段可以再挂 `COST_MISSING`、`FX_MISSING`。候选码即使确认，也只能再挂提示，不能把 `matched` 改成未匹配。

## 4. 匹配三态

数据模型里的 `match.status` 只有 `matched` 和 `partial`。未匹配不是第三个枚举值。未匹配是：这个订单类组没有 match 记录，并且至少有一条未关闭的异常。

### matched

同时满足：

- SKU 已映射。
- 用 `order_id`（Amazon 字段名 `order-id`，Shopify 字段名 `Order`）和 SKU 找到订单。Shopify 的 SKU 来自订单表，不是打款文件。
- 收款行数量与订单 `qty` 一致。没有数量列时，不能凭空造一个数量去比。见开放问题。
- 订单 `item_price` 有值时，收款 Principal 与它相等，且 `currency` 相同。`item_price` 为空则不做金额比较。空金额样本未覆盖。
- Shopify 还要求同一行 `Net` 等于 `Amount` 减 `Fee`。不等则不是 matched。这是样本答案，不是推断。

`matched` 可以同时带着不否定匹配的异常：`COST_MISSING`、`FX_MISSING`，以及确认后的候选提示。

### partial

推断，待 maken 确认。建议只用于这一种情况：

- 订单表能找到该订单和 SKU。
- 本期结算里只有退款或拒付，没有 `Order` 或 Shopify `charge` 收款行。
- 因此没有本期 Principal 可以和 `item_price` 比。不报 `AMOUNT_MISMATCH`，也不把退款轧进货款。
- 写入 `match.status=partial`。不计入未匹配。

合成样本里的全额退款、部分退款、拒付都带了原收款行，所以是 `matched`，不是 `partial`。只有退款、原收款在别的账期：样本未覆盖。

下面这些不是 `partial`：

- 多收费。匹配仍然成功，状态是 `matched`。
- 在途、未打款。没有可匹配的已结算行，不写 match 记录。
- 数量不符、货款不符、SKU 未映射、结算有而订单无。这些是未匹配。
- 银行一边缺记录。v0.1 不做。

### 未匹配

订单类结算行组没有 match 记录。必须有至少一条 `open` 异常。正式未匹配原因码是：

`NOT_IN_ERP`、`REFUND_WITHOUT_ORDER`、`QTY_MISMATCH`、`AMOUNT_MISMATCH`、`SKU_UNMAPPED`。

`CURRENCY_MISMATCH` 是否也算未匹配：推断为算，因为不能安全比金额。样本未覆盖，待确认。

订单有、结算没有，不是结算行组。它不进入匹配率分母，也不叫未匹配组。它走「待下期」或 `NOT_IN_SETTLEMENT`。

## 5. 匹配率

定义以 `EXPECTED.md` 为准：已匹配的订单类结算行组数，除以全部订单类结算行组数。

- 进入分母：Amazon 的订单类组，以及 Shopify 的订单类组。
- 不进入分母：非订单类行，例如 `transaction-type=other-transaction`。重复行不另计一组。`amazon_us_unbalanced.tsv` 整文件不进入分母。
- 计入未匹配：上一节列出的五个正式码。Shopify `Net` 不等于 `Amount - Fee` 使用 `AMOUNT_MISMATCH`，计入未匹配。
- 合成样本：分母 120，已匹配 114，未匹配 6，匹配率 0.95。

「是否影响匹配率分母」在下面写成四种：

| 写法 | 意思 |
|---|---|
| 未匹配组 | 该组进入分母，并计入未匹配 |
| 已匹配组 | 该组进入分母，仍算已匹配 |
| 排除 | 不进入分母 |
| 订单侧 | 不是结算行组，不进入分母 |

## 6. 宽限期和待下期

这是 `NOT_IN_SETTLEMENT` 与候选 `SETTLEMENT_DELAYED` 的边界。

订单没有对应的已结算收款，或 Shopify 行的 `Payout Status` 不是已打款，就看下单日期：

```text
cutoff = period_end - GRACE_DAYS
若 order_date < cutoff：报 NOT_IN_SETTLEMENT，严重度 error
否则：标「待下期」，不算错
```

`Payout Status=paid` 在合成样本里当作已打款。`pending` 当作未打款。这两个取值待真实数据验证。未知状态不要当成已打款。未知状态样本未覆盖。

按推断的自然月月末，期间 `2026-10` 的 `period_end` 是 2026-10-31，cutoff 是 2026-10-17。样本里的三笔在途都落在宽限期内：

| 订单 | 下单日期 | 当前应有的结果 |
|---|---|---|
| `SYN-US-INTRANSIT` | 2026-10-25 | 待下期，不报错 |
| `SYN-DE-INTRANSIT` | 2026-10-31 | 待下期，不报错 |
| `SYN-SH-PENDING` | 2026-10-18 | 待下期。打款文件有这一行，但 `Payout Status=pending`，不算已结算 |

`anomalies.json` 这三行的 `expected_issue_kind` 写的是 `NOT_IN_SETTLEMENT`。旁边的 note 写明：只有超过 14 天才报，否则标待下期。W3 不要把这三行理解成「现在就要输出一条 error」。超过宽限期的正例：样本未覆盖。

若 `period_end` 改成文件里的 `settlement-end-date`（2026-10-14），cutoff 是 2026-09-30。这三笔同样不报错。样本不能替 maken 选定哪一种 `period_end`。

## 7. 分类总表

正式码 13 个，来自实施方案 6.1。另外 5 个码 maken 已于 2026-11-02 确认，写入 `IssueKind`。

| 码 | 中文名 | 状态 | 严重度 | 匹配率 | 样本 |
|---|---|---|---|---|---|
| `NOT_IN_ERP` | 结算有，订单表没有 | 正式 | error | 未匹配组 | `not_in_erp` |
| `NOT_IN_SETTLEMENT` | 订单过了宽限期仍未结算 | 正式 | error | 订单侧 | 超期正例未覆盖 |
| `QTY_MISMATCH` | 数量不符 | 正式 | error | 未匹配组 | `qty_mismatch` |
| `AMOUNT_MISMATCH` | 金额不符 | 正式 | error | 未匹配组 | `amount_mismatch`、`shopify_net_mismatch` |
| `SKU_UNMAPPED` | SKU 没映射 | 正式 | error | 未匹配组 | `sku_unmapped` |
| `COST_MISSING` | 缺成本 | 正式 | error | 已匹配组 | `cost_missing` |
| `FX_MISSING` | 缺汇率 | 正式 | error | 已匹配组 | `fx_missing`（要换汇率文件） |
| `CURRENCY_MISMATCH` | 币种不一致 | 正式 | error | 未匹配组（推断） | 样本未覆盖 |
| `DUPLICATE_ROW` | 文件内完全重复的行 | 正式 | warn | 排除 | `duplicate_row` |
| `REFUND_WITHOUT_ORDER` | 有退款，没有原订单 | 正式 | error | 未匹配组 | `refund_without_order` |
| `UNKNOWN_FEE_TYPE` | 不认识的费用或交易类型 | 正式 | warn | 排除 | `unknown_fee_type` |
| `SETTLEMENT_UNBALANCED` | 结算单自身不平 | 正式 | error | 排除 | `settlement_unbalanced` |
| `PARSE_ERROR` | 这一行没读成 | 正式 | error | 排除 | 样本未覆盖 |
| `FEE_OVERCHARGE` | 配送费高于参考 | maken 已于 2026-11-02 确认 | warn | 已匹配组 | `fee_overcharge` |
| `SETTLEMENT_DELAYED` | 待下期 | maken 已于 2026-11-02 确认 | info | 订单侧 | `in_transit` 三笔 |
| `CHARGEBACK` | 拒付单独提示 | maken 已于 2026-11-02 确认 | info | 已匹配组 | `chargeback` 两笔 |
| `PARTIAL_REFUND` | 部分退款提示 | maken 已于 2026-11-02 确认 | info | 已匹配组 | `partial_refund` |
| `DUPLICATE_SETTLEMENT` | 两个结算里都有收款 | maken 已于 2026-11-02 确认 | error | 已匹配组（计法待确认） | 样本未覆盖 |

人话模板里的 `{名字}` 是占位符。展示时替换，不把花括号留给用户。

### NOT_IN_ERP

- 中文名：结算有，订单表没有。
- 状态：正式。
- 触发条件：订单类组的 SKU 已在映射表（Amazon 用结算 `sku`；表头是 `店铺,平台SKU,内部SKU,标题`）。按 `order-id` + `sku` 找不到订单。组内并不全是 `transaction-type=Refund`。Shopify 按 `Order` 找不到订单，且该组不是纯 `Type=refund`。
- 严重度：error。
- 匹配率：未匹配组。
- 人话模板：订单 {order_id}（SKU {sku}）在结算里有记录，订单表里没有。请核对是不是漏导入了订单，或订单号、SKU 写错了。
- 建议处理：补导入订单，或确认这是平台有、自家没有的单。不要凭结算行新建一笔订单金额。
- 合成样本：`not_in_erp`。`amazon_us_2026-10-01_2026-10-14.tsv` 第 291–293 行，订单 `SYN-US-NOT-IN-ERP`，SKU `CUP-US-001`。SKU 在映射表里，所以不是 `SKU_UNMAPPED`。
- 样本未覆盖：组内同时有收款和退款、但订单表没有；只有拒付、订单表没有。后一种按现有伪代码会落到本码，不会落到 `REFUND_WITHOUT_ORDER`。见开放问题。

### NOT_IN_SETTLEMENT

- 中文名：订单过了宽限期仍未结算。
- 状态：正式。
- 触发条件：订单没有已结算的对应收款，且 `order_date < period_end - GRACE_DAYS`。已结算不包括 Shopify `Payout Status=pending`。字段用订单表的 `order_date`，不用结算的 `posted-date`。
- 严重度：error。
- 匹配率：订单侧。不进入分母。
- 人话模板：订单 {order_id}（SKU {sku}）的下单日期是 {order_date}，到对账期末 {period_end} 已经超过 {grace_days} 天，仍然没有已结算记录。
- 建议处理：先查下一期结算是不是没导入。确认确实没有结算后，再由人处理。系统不自动关掉。
- 合成样本：超期后才报错的正例，样本未覆盖。`in_transit` 三笔只覆盖宽限期内的另一侧，当前不得输出本码。见第 6 节。

### QTY_MISMATCH

- 中文名：数量不符。
- 状态：正式。
- 触发条件：Amazon 收款行按订单项取一次的 `quantity-purchased` 不等于订单 `qty`。不把费用行的数量加总，不用 Refund 行的数量。
- 严重度：error。
- 匹配率：未匹配组。报了本码就不再报 `AMOUNT_MISMATCH`。
- 人话模板：订单 {order_id}（SKU {sku}）结算数量是 {qty_settlement}，订单表数量是 {qty_order}。
- 建议处理：对照原始行。数量没核清之前，不要先去改货款判断。
- 合成样本：`qty_mismatch`。同一文件第 282–284 行，订单 `SYN-US-QTY`，SKU `MUG-US-002`。结算数量 1，订单 `qty` 3。Principal 与 `item_price` 一致，仍然只报数量。订单表第 116 行。
- 不得误报：`partial_refund` 的 Refund 行 `quantity-purchased` 为 0，Order 行数量仍是 2，与订单 `qty` 相同。不得报本码。
- 样本未覆盖：Shopify。官方基础列没有数量。没有数量列时不报本码。这是推断，待确认。

### AMOUNT_MISMATCH

- 中文名：金额不符。
- 状态：正式。
- 触发条件有两条，用同一原因码。
  - Amazon：数量已经一致。只合计 `transaction-type=Order` 且 `amount-description=Principal` 的 `amount`。该合计不等于订单 `item_price`。Refund、Chargeback 的 Principal 不轧进这个合计。
  - Shopify：同一行 `Net` 不等于 `Amount` 减 `Fee`。这是官方列之间的勾稽，不是和 `item_price` 比。
- 严重度：error。
- 匹配率：未匹配组。两条都计入未匹配。
- 人话模板：订单 {order_id}（SKU {sku}）的结算货款是 {principal}，订单金额是 {item_price}，差额 {diff}。退款和拒付没有轧进这笔货款。
- 人话模板：订单 {order_id} 的净额 {net} 不等于金额 {amount} 减费用 {fee}。按表计算应为 {expected_net}，差额 {diff}。
- 建议处理：打开原始行核对。不要用退款把货款轧平后再判断。差额不会自动修正。
- 合成样本：
  - `amount_mismatch`。同一 Amazon 文件第 285 行，订单 `SYN-US-AMT`，SKU `BAG-US-003`。Order Principal 22.00，订单 `item_price` 25.00。数量一致。订单表第 117 行。
  - `shopify_net_mismatch`。`shopify_payout_2026-10-21.csv` 第 7 行，订单 `SYN-SH-NET`。`Amount` 20.00，`Fee` 0.40，`Net` 19.00。20.00 减 0.40 应为 19.60。订单仍在订单表第 119 行，`item_price` 也是 20.00。这条不符的是净额勾稽，不是商品金额。
- 不得误报：`refund` 场景有 Order Principal 50.00 和 Refund Principal -50.00。只拿 50.00 去比订单金额，匹配成功。
- 样本未覆盖：Shopify 的 `Amount` 不等于 `item_price`。不要把 `SYN-SH-NET` 写成商品金额不符。

### SKU_UNMAPPED

- 中文名：SKU 没映射。
- 状态：正式。
- 触发条件：结算 `sku` 在该店铺的映射表里找不到。先于订单查找。映射表列是 `店铺`、`平台SKU`、`内部SKU`、`标题`。
- 严重度：error。
- 匹配率：未匹配组。
- 人话模板：结算 SKU {sku}（订单 {order_id}）不在 SKU 映射表里，对不上内部 SKU。
- 建议处理：补上这家店的平台 SKU。补上之前，这组不算匹配成功。不要猜一个内部 SKU。
- 合成样本：`sku_unmapped`。同一 Amazon 文件第 288–290 行，订单 `SYN-US-UNMAPPED`，SKU `SYN-UNMAPPED`。订单在订单表第 118 行。因为先查映射，期望只有本码，不另报 `NOT_IN_ERP`。
- 样本未覆盖：Shopify。打款文件没有 SKU 列。

### COST_MISSING

- 中文名：缺成本。
- 状态：正式。
- 触发条件：订单已经匹配。用映射后的内部 SKU 和订单 `order_date`，在成本表找不到覆盖该日期的生效行。成本表列是 `内部SKU`、`采购单价`、`头程单价`、`币种`、`生效日期`。样本没有失效日期列。推断：一条成本从它的生效日期起，直到同一内部 SKU 下一条生效日期之前有效。没有任何一条早于或等于订单日期，就是缺失。
- 严重度：error。利润算不出来。这不否定匹配。
- 匹配率：已匹配组。
- 人话模板：订单 {order_id} 已对上，但内部 SKU {internal_sku} 在 {order_date} 没有生效的采购成本。利润先不算。
- 建议处理：补这条 SKU 在该日期能用的采购单价和头程单价。不要估一个成本。
- 合成样本：`cost_missing`。同一 Amazon 文件第 279–281 行，订单 `SYN-US-COST`，SKU `COST-GAP-US`，内部 SKU `INT-COST-GAP`。成本表只有生效日期 2026-11-01。订单日期 2026-10-06，覆盖不到。订单表第 112 行。
- 成本币种和结算币种不同，本身不是本码，也不是 `CURRENCY_MISMATCH`。样本成本是 CNY，结算是 USD 或 EUR。折算靠汇率表。缺汇率另报 `FX_MISSING`。

### FX_MISSING

- 中文名：缺汇率。
- 状态：正式。
- 触发条件：订单已经匹配，利润要换成人民币时，汇率表没有该月、该结算币种兑 CNY 的行。汇率表列是 `月份`、`原币`、`目标币`、`汇率`。目标币在 v0.1 只使用 CNY。这是实施方案 6.3 的规则，不是平台字段。不调用实时汇率，不拿别的月份顶上。
- 严重度：error。人民币利润算不出来。这不否定匹配。
- 匹配率：已匹配组。
- 人话模板：订单 {order_id} 已对上，但 {period} 没有 {from_ccy} 兑 {to_ccy} 的汇率。人民币利润先不算。
- 建议处理：在汇率表补该月该币对。不要用网上汇率或上月汇率填上。
- 合成样本：`fx_missing`。`amazon_de_2026-10-01_2026-10-14.tsv` 第 39–41 行，订单 `SYN-DE-FX`，SKU `BOT-DE-001`。只有把 `fx_rates.csv` 换成 `fx_rates_missing_eur.csv` 时，2026-10 才没有 EUR 兑 CNY。默认汇率表有这行，不会产生本码。金额原文含 `95,00`。订单表第 113 行。

### CURRENCY_MISMATCH

- 中文名：币种不一致。
- 状态：正式。
- 触发条件：要比的两边币种不同。订单侧用 `currency`。Amazon 结算侧用已核实列 `currency`。Shopify 官方基础列没有币种；实施方案 5.2 把可选列 `Currency` 标为待真实数据验证。没有该列时，币种来自导入参数或店铺默认币种，不是从打款文件里读出来的。结算币种和订单币种不同，才报本码。
- 不触发：成本表的 `币种` 是 CNY、结算是 USD。这是正常的，走汇率，不报本码。
- 严重度：error。
- 匹配率：推断为未匹配组，因为不能安全比金额。待确认。样本未覆盖。
- 人话模板：订单 {order_id}（SKU {sku}）的订单币种是 {currency_order}，结算币种是 {currency_settlement}，不能直接比金额。
- 建议处理：核对是不是导错店铺或币种。不要把两种币种的数字相减。
- 合成样本：样本未覆盖。

### DUPLICATE_ROW

- 中文名：文件内完全重复的行。
- 状态：正式。
- 触发条件：同一文件里，后一行与前一行每个字段都相同。第二行是重复行。原始行保留。不把它再写成另一条结算明细，也不另计一组。文件总额仍含这两行。这是样本说明。
- 严重度：warn。第一行仍可参与匹配。
- 匹配率：排除。不另计一组。
- 人话模板：文件 {source_file} 第 {row_no} 行与前面某一行完全相同，已标为重复行。原始行仍保留，不再计成另一组。
- 建议处理：确认是不是导出时复制了一行。不要把这一行再加进订单金额。
- 合成样本：`duplicate_row`。`amazon_us_2026-10-01_2026-10-14.tsv` 第 6 行与第 5 行完全相同。订单 `SYN-US-0001`，SKU `CUP-US-001`。
- 这不是「两个结算单里各有一笔收款」。那种见候选 `DUPLICATE_SETTLEMENT`。

### REFUND_WITHOUT_ORDER

- 中文名：有退款，没有原订单。
- 状态：正式。
- 触发条件：组内每一行都是退款，并且订单表没有这个订单。Amazon 的退款取值是 `transaction-type=Refund`，待真实数据验证。SKU 已经能映射，所以不是 `SKU_UNMAPPED`。
- 严重度：error。
- 匹配率：未匹配组。
- 人话模板：订单 {order_id}（SKU {sku}）只有退款，订单表里没有原订单。
- 建议处理：查是不是上一期的订单没导入。不要把它当成一笔新的销售。
- 合成样本：`refund_without_order`。同一 Amazon 文件第 294–295 行，订单 `SYN-US-REFUND-NO-ORDER`，SKU `CUP-US-001`。
- 样本未覆盖：Shopify `Type=refund` 且订单表没有；只有拒付、没有原订单。

### UNKNOWN_FEE_TYPE

- 中文名：不认识的费用或交易类型。
- 状态：正式。
- 触发条件：Amazon 的 `amount-type` + `amount-description` 不在已知费用组合里。合成已知组合只在 `scripts/sample_vocab.py` 的 `KNOWN_FEE_PAIRS`，不是平台全集，每条都待真实数据验证。不认识时仍入库，费用类别暂记 other，不猜。Shopify 的 `Type` 不在已知取值里时，原样保存，并使用本码。这是 T11 的任务说明。Shopify 未知 Type：样本未覆盖。
- 严重度：warn。行还在，只是还不能归进已知费用。
- 匹配率：排除。样本里的未知费用是 `transaction-type=other-transaction`，没有订单号，不进分母。若未知费用挂在订单行上：样本未覆盖。推断：不因此把该订单组算成未匹配，另挂本码。待确认。
- 人话模板：文件 {source_file} 第 {row_no} 行的费用类型不认识：{amount_type} / {amount_description}。这一行已保留，没有猜分类。
- 人话模板：文件 {source_file} 第 {row_no} 行的交易类型 {transaction_type} 不在已知取值里。已原样保留。
- 建议处理：人工确认它属于哪一类。确认前不要把它算进已知佣金或配送费。
- 合成样本：`unknown_fee_type`。同一 Amazon 文件第 296 行。`amount-description=SyntheticUnknownFee`，`transaction-type=other-transaction`。没有订单号，没有 SKU。

### SETTLEMENT_UNBALANCED

- 中文名：结算单自身不平。
- 状态：正式。
- 触发条件：同一 Amazon `settlement-id` 下，明细行 `amount` 之和不等于汇总行 `total-amount`。明细不含汇总行。汇总行的识别是 `transaction-type` 为空且 `total-amount` 非空。这是推断，待真实数据验证。
- 严重度：error。
- 匹配率：排除。该文件不进入分母。
- 人话模板：结算单 {settlement_id} 的总额是 {total_amount}，明细合计是 {line_sum}，差额 {diff}。这张单不进入匹配率。
- 建议处理：不要用这张单做对账结论。重新下载或核对汇总行。差额不会自动抹平。
- 合成样本：`settlement_unbalanced`。`amazon_us_unbalanced.tsv` 第 2 行是汇总。`total-amount` 6.00，明细合计 5.00。
- 和实施方案 6.2 的差别：伪代码报完不平后，仍会继续拿明细去做订单匹配。这个文件里的订单 `SYN-US-UNBAL-1` 不在订单表，继续匹配就会再冒出 `NOT_IN_ERP`。`anomalies.json` 只列了本码。两种做法都写在开放问题里，确认前不要当成已定。
- 样本未覆盖：Shopify。官方基础列没有打款总额。T11 用各行 `Net` 相加当作总额，这样自己和自己比永远平。不编造打款总额列。

### PARSE_ERROR

- 中文名：这一行没读成。
- 状态：正式。
- 触发条件：来自已写进任务的导入规则，不是平台新字段。
  - 单行解析失败：留下本码，继续下一行，不中断整批。
  - Amazon 金额按站点解析失败：该行本码。
  - 多出的未知列：内容留在原始行，本码的严重度是 info，说明未知列已保留。T10 写明若要另设原因码，先问 maken。本文不另设。
  - 成本表两段生效期重叠：本码。
  - 整批缺少必需列：整批失败，不把「整批失败」伪装成一行本码。
- 严重度：行不能使用时是 error。未知列已保留时是 info。
- 匹配率：排除。没读成的行不是订单类组。
- 人话模板：文件 {source_file} 第 {row_no} 行没能按规则读入：{error}。这一行已留下，整批没有因此中断。
- 人话模板：文件 {source_file} 有未识别的列 {column_name}。列内容已保留，不参与算钱。
- 建议处理：按提示改源文件或映射后重导这一行。不要猜一个金额填上。
- 合成样本：样本未覆盖。现有合成文件都能按生成器自己的格式读。不要为了凑这条去改样本。

## 8. 已确认的新增原因码

下面五个码 maken 已于 2026-11-02 全部确认。它们写入 `IssueKind`。对账代码可以输出它们。利润算法仍按各码自己的说明，不因确认而改计算。

### FEE_OVERCHARGE

- 中文名：配送费高于参考。
- 状态：maken 已于 2026-11-02 确认。
- 借鉴：第一个公开仓库把「费用和预期不一致」单独看。我们只对用户自己提供的参考表做这件事，不复制它的判定或文字。
- 触发条件：匹配已经成功。Amazon 收款行里，`amount-type=ItemFees` 且 `amount-description=FBAPerUnitFulfillmentFee`。这两个取值待真实数据验证。费用绝对值，大于 `fee_reference.csv` 的 `expected_fba_fee_per_unit` 乘以数量。数量同样只取一次，不把三行费用的数量加总。参考表列是本项目的 `platform_sku`、`currency`、`expected_fba_fee_per_unit`，不是亚马逊费率字段，也不是真实费率。结算 `currency` 必须等于参考表 `currency`。币种不同时不报本码。
- 草案阈值：严格大于参考合计就提示。不设百分比，不设绝对差额门槛。待确认。
- 严重度：warn。
- 匹配率：已匹配组。匹配仍然成功。
- 人话模板：订单 {order_id}（SKU {sku}）的配送费是 {fee_amount}，参考是每件 {fee_reference}。按数量 {qty} 计算，参考合计是 {fee_expected}。这单仍然算对上了。
- 建议处理：对照平台费用说明。这只是提示，不改利润，也不把这单算成没对上。
- 合成样本：`fee_overcharge`。同一 Amazon 文件第 262–264 行，订单 `SYN-US-FEE`，SKU `CUP-US-001`。FBA 行金额 -5.50，数量取一次是 1，参考 3.50。订单表第 108 行。`anomalies.json` 写的是 `FEE_OVERCHARGE?`。确认前正式原因码仍为空。
- 样本未覆盖：佣金高于参考。参考表没有佣金列，不编造。Shopify 的 `Fee` 高于某个费率：没有参考列，样本未覆盖。

### SETTLEMENT_DELAYED

- 中文名：待下期。
- 状态：maken 已于 2026-11-02 确认。
- 借鉴：第一个公开仓库把「结算明显晚于预期」单独看。我们的边界是自己的 `GRACE_DAYS`，不是它的延迟定义。
- 触发条件：与 `NOT_IN_SETTLEMENT` 同一组事实，但 `order_date` 还没有早于 `period_end - GRACE_DAYS`。包括 Shopify `Payout Status=pending` 且仍在宽限期内。
- 和正式码的边界：宽限期内只提示、不报错；过了宽限期才用 `NOT_IN_SETTLEMENT`，并且不再用本候选码。不要两个一起报。
- 严重度：info。
- 匹配率：订单侧。不进入分母。
- 它是原因码还是只是一个状态：待确认。若 maken 不要新码，界面仍应显示「待下期」，只是不写进 `issue.kind`。
- 人话模板：订单 {order_id}（SKU {sku}）下单日期 {order_date}，还在 {grace_days} 天内，先标待下期，不算错。
- 人话模板：订单 {order_id} 在打款导出里，但打款状态是 {payout_status}，还不能当成已结算。下单日期 {order_date}，仍在宽限期内，标待下期。
- 建议处理：等下一期结算。未超过宽限期时，不要当成漏单。
- 合成样本：`in_transit` 三笔。见第 6 节。`SYN-SH-PENDING` 在 `shopify_payout_2026-10-21.csv` 第 6 行，订单表第 115 行。

### CHARGEBACK

- 中文名：拒付单独提示。
- 状态：maken 已于 2026-11-02 确认。
- 来源：本项目 T08 场景，不是外部仓库的原因码。
- 触发条件：能匹配到原订单，并且存在拒付行。Amazon 用 `transaction-type=Chargeback`。Shopify 用 `Type=dispute`。两个取值都待真实数据验证。确认前，利润仍按退款类计入，不单列。
- 严重度：info。推断。
- 匹配率：已匹配组。不改变匹配。
- 人话模板：订单 {order_id}（SKU {sku}）有一笔拒付，金额 {amount}。目前按退款计入利润。这只是单独提示，匹配仍然成功。
- 建议处理：若要在利润表把拒付和普通退款分开，先确认。确认前不改利润算法。
- 合成样本：
  - Amazon：`amazon_us_2026-10-01_2026-10-14.tsv` 第 278 行，订单 `SYN-US-CB`，SKU `CUP-US-001`。原 Order 在第 275–277 行。订单表第 111 行。当前期望原因码为空。
  - Shopify：`shopify_payout_2026-10-21.csv` 第 8 行，订单 `SYN-SH-CB`，`Type=dispute`，金额 -35.00。原 `charge` 在 `shopify_payout_2026-10-07.csv` 第 6 行。当前期望原因码为空。
- 样本未覆盖：只有拒付、没有原订单；拒付的手续费或原因字段。不编造这些字段。

### PARTIAL_REFUND

- 中文名：部分退款提示。
- 状态：maken 已于 2026-11-02 确认。
- 来源：本项目 T08 场景。
- 触发条件：同一订单和 SKU 上，退款 Principal 的绝对值大于 0，且小于收款 Principal。收款行数量与订单 `qty` 相同。这不是数量不符，也不是货款不符。
- 严重度：info。推断。
- 匹配率：已匹配组。
- 人话模板：订单 {order_id}（SKU {sku}）只退了一部分。退款货款 {refund_principal}，原货款 {principal}。数量没有变，这单仍然算对上了。
- 建议处理：只提示有部分退款。不要因为退款行数量为 0 就报数量不符。利润仍按实际退款额计。
- 合成样本：`partial_refund`。同一 Amazon 文件第 270–274 行，订单 `SYN-US-PARTIAL`，SKU `BAG-US-003`。Order Principal 60.00，Refund Principal -10.00。Order 行数量 2，与订单 `qty` 相同。订单表第 110 行。当前期望原因码为空。
- 全额退款不是本码。`SYN-US-REFUND` 的退款货款绝对值等于原货款，匹配成功，不提示部分退款。

### DUPLICATE_SETTLEMENT

- 中文名：两个结算里都有收款。
- 状态：maken 已于 2026-11-02 确认。
- 借鉴：第一个公开仓库把「同一笔有多条结算」单独看。我们的判定用自己的结算标识，不复制它的实现。
- 触发条件：同一个 `order-id` + `sku`（Shopify 用同一个 `Order`）的收款，出现在两个不同结算里。Amazon 的结算标识用 `settlement-id`。Shopify 没有官方打款总额标识；`Payout ID` 待真实数据验证。没有该列时，只能暂用 `Payout Date` 区分打款批次。这是推断，待确认。两笔都必须是收款：Amazon `transaction-type=Order` 且 Principal 为正；Shopify `Type=charge` 且 `Amount` 为正。一笔收款加一笔退款不是本码。
- 严重度：error。推断。不自动删任何一行。
- 匹配率：草案仍算已匹配组，避免没确认就改匹配率。是否把其中一组算未匹配，待确认。
- 人话模板：订单 {order_id}（SKU {sku}）在结算 {settlement_id_a} 和 {settlement_id_b} 里都有收款。请核对是不是同一笔钱记了两次。
- 建议处理：人工核对两张结算。不要自动删掉其中一笔，也不要自动改利润。
- 合成样本：样本未覆盖。文件内完全相同的两行是 `DUPLICATE_ROW`，不是本码。

## 9. 不应报错的样本

这些场景的正式原因码为空。确认前也不得输出候选码。

| 场景 | 订单 | 应有结果 |
|---|---|---|
| `normal` | `SYN-US-0001` | 匹配成功。代表行，不是全部正常单 |
| `refund` | `SYN-US-REFUND` | 按订单号合并后匹配成功。利润里退款为负。不得报 `AMOUNT_MISMATCH` |
| `partial_refund` | `SYN-US-PARTIAL` | 匹配成功。不得报 `QTY_MISMATCH` |
| `chargeback` | `SYN-US-CB`、`SYN-SH-CB` | 匹配到原订单，按退款类计入利润 |
| `fee_overcharge` | `SYN-US-FEE` | 匹配成功。候选码未确认，正式原因码为空 |
| `in_transit` | 第 6 节三笔 | 待下期，不报 `NOT_IN_SETTLEMENT` |

本样本没有生成仓储费、移除费、FBA 赔偿、促销。不是费用全集。真实文件里如果有，应进 `UNKNOWN_FEE_TYPE`，不要猜。

## 10. 确定性规则和 AI 的分工

v0.1 没有 AI。原因码、匹配状态、金额、利润都只由代码判定。

v0.5 若接上模型，模型只能做实施方案 6.5 已经列出的事：列映射建议、费用分类建议、异常解释草稿、带引用的问答。建议工具只生成待审批项，不写账。

分工按下面执行。后三条借鉴第二个公开仓库的思路，链接见第 2 节。实现未核实。

- 规则写入原因码和 `match.status`。模型不能改写这些结果，不能改金额，不能改利润。
- 模型可以写解释草稿和建议动作。用户确认前，草稿不是结论。
- 模型只能建议更严的处理。例如规则给出「待下期」，模型可以建议先人工复核。模型不能把异常关掉，不能把 error 改成已解决，不能把未匹配说成已匹配。
- 读不出的金额、缺失的汇率、缺失的成本：规则已经交出异常。模型不得补一个数。
- v0.1 的网页是只读报表。即使以后能填处理说明，没有人确认也不许自动变更。

## 11. 置信度和自动处理

v0.1 不计算置信度，不自动关闭，不自动忽略，不自动解释。

每条异常保持 `open`，直到以后的人工流程改状态。忽略必须有人填写理由。那是更后面的网页任务，不是 v0.1。

以后可以考虑：规则命中很明确时，仍只给出建议，人确认后才改状态。这是推断，不是 v0.1 的范围。高置信度也不等于可以自动关单。

## 12. 开放问题

maken 已确认以下口径（2026-11-03）。

- [x] `FEE_OVERCHARGE` 进入正式原因码；严格大于参考值才报，使用绝对差额，当前容差为 `0.00`，只比较已有参考表的费用类别。
- [x] `SETTLEMENT_DELAYED` 作为独立原因码，同时在界面显示「待下期」。
- [x] `period_end` 使用自然月最后一天。
- [x] `CHARGEBACK` 单独统计和提示；利润继续并入退款，不另改利润口径。
- [x] `PARTIAL_REFUND` 作为 `info` 提示，不影响匹配成功。
- [x] `DUPLICATE_SETTLEMENT` 纳入 v0.1；第二笔重复收款不计入匹配成功；Shopify 没有 `Payout ID` 时使用 `Payout Date` 区分批次。
- [x] `partial` 只用于「本期只有退款或拒付、原订单存在、没有收款行」的情况。
- [x] 只有拒付且没有原订单时使用 `REFUND_WITHOUT_ORDER`。
- [x] `CURRENCY_MISMATCH` 计入未匹配。
- [x] 不平衡结算单只报 `SETTLEMENT_UNBALANCED`，不继续用明细做匹配。
- [x] 未知费用出现在订单行上时仍算已匹配，另挂 `UNKNOWN_FEE_TYPE`。
- [x] Shopify 没有数量列时不报 `QTY_MISMATCH`。
- [x] 未知列继续使用 `PARSE_ERROR`，严重度保持 `error`；不新增原因码。
- [x] `normalize(sku)` 只去掉首尾空白，不改变大小写或其他字符。

## 13. 本文没有做的事

- 没有写对账代码，没有改 `IssueKind`，没有把候选码写进枚举。
- 没有克隆或引用两个公开仓库的代码。
- 没有把未核实的平台取值写成事实。`transaction-type`、`amount-type`、`amount-description`、Shopify `Type`、`Payout Status` 的全集都待真实数据验证。
