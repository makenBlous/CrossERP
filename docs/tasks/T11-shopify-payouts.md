# T11 Shopify Payments 打款 CSV 导入器

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 1 天 | T08, T09 | `task/T11-shopify-payouts` |

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

- `settlement_line` 没有状态列。`Payout Status` 写在 `amount_description`，格式 `payout_status=<原文>`。这是推断。若要单独列，需要改表。
- 没有 `Payout ID` 时，`external_id` 用 `payout-date:<原文>`。空日期用 `payout-date:missing`。同一平台外部单号全局唯一。两份文件打款日相同会整批失败。要不要把店铺或文件名放进外部单号，需要 maken 决定。
- 文件没有店铺列。未传入时店铺名是 `Shopify`，站点是 `shopify`。推断。T13 用 `mapping.defaults` 的 `currency`、`marketplace`、`store_name` 传入。连接器不查库。
- `Type`、`Payout Status`、日期格式、金额是否永远是 US 格式，都待真实数据验证。见 `docs/data-formats/shopify-payouts.md`。
- 本地只跑了 SQLite。MySQL / PostgreSQL 没有本机服务，未跑。

## 完成记录

本地只用 SQLite。解释器是 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。`PYTHONPATH` 指向本 worktree 的 `src`。没有用 `uv run`。没有跑 MySQL / PostgreSQL。

```text
pytest tests/golden/test_shopify.py -q
15 passed in 1.38s

pytest -m db -k shopify -q
5 passed, 113 deselected, 1 warning in 2.27s

mypy
Success: no issues found in 37 source files

pytest -q
117 passed, 1 skipped, 1 warning in 4.98s
```

没有 Payout ID 时按 `Payout Date` 分组。这是推断。`dispute` 入库为 `transaction_type=chargeback`。`Net` 不符仍按原文入库，并写 1 条 `AMOUNT_MISMATCH`。未改 `docs/tasks/README.md`。未改 `audit/chain.py`。
