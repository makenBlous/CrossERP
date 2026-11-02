# T11 Shopify Payments 打款 CSV 导入器

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W2 | 1 天 | T08, T09 | `task/T11-shopify-payouts` |

## 目标
导入 Shopify 后台 Finance > Payouts 导出的交易 CSV，生成 `settlement`（一次打款）+ `settlement_line`（一笔交易），校验 `Net = Amount − Fee`。

## 背景
- 实施方案 5.2、8 W2 第 2 条。
- 官方基础列（https://help.shopify.com/en/manual/payments/shopify-payments/payouts/view-details）：`Transaction Date, Type, Order, Card Brand, Card Source, Payout Status, Payout Date, Available On, Amount, Fee, Net`。
- 非官方资料（https://storepaperwork.com/guides/shopify-payments-transactions-export-columns-explained/）提到的 `Checkout, Payment Method Name, Presentment Amount, Presentment Currency, Currency, Payout ID` 为可选列，「待真实数据验证」。

## 范围
- `connectors/shopify_payouts/connector.py`，`id = "shopify.payouts"`，`kind = "payout"`。
- `sniff()`：表头含 `Payout Date`、`Amount`、`Fee`、`Net`、`Type` → 0.9。
- 按表头名取列；11 个基础列缺任何一个 → 整批失败并列出；可选列缺失不报错，存在则保存。
- 分组：有 `Payout ID` 按它分组；没有则按 `Payout Date` 分组（推断，PR 中注明）。每组 → 1 个 `settlement`，`total = ΣNet`。
- 金额：US 格式（Shopify 导出格式「待真实数据验证」；若出现逗号小数，按 `Currency` 列选 locale）。
- 币种：有 `Currency` 列用它；否则用 CLI 参数 `--currency`（T13）或店铺默认币种；都没有 → 整批失败并提示。
- 每行：`Net ≠ Amount − Fee` → `AMOUNT_MISMATCH`（detail 含三个数和差额）。
- `Type` 的取值映射到 `transaction_type`（如 charge/refund/dispute/adjustment，**待真实数据验证**），未知 Type → 原样保存 + `UNKNOWN_FEE_TYPE`。
- `Payout Status` 非已打款（如 pending/in_transit，取值待真实数据验证）的行：照常导入，`settlement_line` 记录状态，供 W3 的「在途」判断。
- `Transaction Date` 带时区 → UTC。

## 不做
- 不调 Shopify API；不处理 Shopify 订单导出（以后用 generic_mapped）。

## 步骤
1. golden 期望从 T08 expected 推导，先写测试。
2. 实现 + entry point。
3. 测试：两个样本 golden 相等；Net 不符 → 1 条 `AMOUNT_MISMATCH`；dispute 行入库为 chargeback 类；删除可选列后的文件也能导入；列顺序打乱结果相同。
4. 写 `docs/data-formats/shopify-payouts.md`。

## 涉及文件
`src/crosserp/connectors/shopify_payouts/{__init__.py,connector.py,type_map.yaml}` `pyproject.toml` `tests/golden/shopify/**` `tests/golden/test_shopify.py` `docs/data-formats/shopify-payouts.md` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/golden/test_shopify.py -q` | passed |
| 三库分别 `uv run pytest -m db -k shopify -q` | passed |

## maken 人工验收清单
- [ ] 从 Shopify 后台导出一份真实打款 CSV（会发到邮箱），只看表头，把表头一行复制给代理（不要发金额和订单数据）。
- [ ] 读 `docs/data-formats/shopify-payouts.md`，确认 `Type` 取值和你后台看到的一致。

## 问题

## 完成记录
