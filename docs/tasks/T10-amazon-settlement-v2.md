# T10 Amazon 结算报告 Flat File V2 导入器 + 费用分类表

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 2 天 | T08, T09 | `task/T10-amazon-v2` |

## 目标
把 Amazon Seller Central 下载的 Flat File V2 结算报告（tab 分隔）正确导入为 `settlement` + `settlement_line` + `fee`，US/EU 金额格式都对，账不平和不认识的费用都进异常清单。

## 背景
- 实施方案 5.1（字段、EU 小数、汇总行推断、校验）、8 W2 第 1、6 条。
- 官方字段文档：https://developer-docs.amazon/sp-api/docs/report-type-values-settlement （报告类型 `GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2`；欧洲站金额如 `95,00`）。
- 24 个字段：`settlement-id, settlement-start-date, settlement-end-date, deposit-date, total-amount, currency, transaction-type, order-id, merchant-order-id, adjustment-id, shipment-id, marketplace-name, amount-type, amount-description, amount, fulfillment-id, posted-date, posted-date-time, order-item-code, merchant-order-item-id, merchant-adjustment-item-id, sku, quantity-purchased, promotion-id`。
- 「待真实数据验证」：汇总行结构、日期格式、`transaction-type` / `amount-type` / `amount-description` 取值全集。

## 范围
- `connectors/amazon_settlement_v2/connector.py`，`id = "amazon.settlement_v2"`，`kind = "settlement"`，`version = "0.1.0"`。
- `sniff()`：读首行（处理 UTF-8 BOM），按 tab 分割后包含 `settlement-id`、`amount-type`、`amount-description`、`total-amount` → 0.95；否则 0。
- `read()`：`csv` 模块 `delimiter="\t"`，**按表头名取列**；缺少必需列（`settlement-id, total-amount, currency, transaction-type, amount-type, amount-description, amount`）→ 整批失败并列出缺哪几列；多出的未知列保留在 raw_row，并生成 1 条 `PARSE_ERROR`（severity=info，说明「未知列已保留」）——若 maken 认为应另设原因码，先问。
- 汇总行识别：`transaction-type` 为空且 `total-amount` 非空的行 → `settlement` 头；同一文件可能有多个 settlement-id（推断），按 settlement-id 分组处理。
- 金额：`locale_for(marketplace-name, currency)` 选 us/eu，再 `parse_amount()`；解析失败 → 该行 `PARSE_ERROR`。
- 日期：支持实施方案未确定的多种格式（如 `2026-10-14 07:00:00 UTC`、`14.10.2026`、ISO-8601），写成一个 `parse_amazon_date()`，每种格式一条测试，并注明「待真实数据验证」；全部转 UTC。
- `fee_map.yaml`：`(amount-type, amount-description) → fee_category`；初版只收录合成样本 `scripts/sample_vocab.py` 用到的组合，每条注明来源（合成 / 真实文件名）。
- 未知组合 → `fee_category=other` 照常入库 + `UNKNOWN_FEE_TYPE` 异常（detail 含原 type/description、行号）。**不丢数据、不猜分类。**
- 校验：每个 settlement-id 的 Σ交易行 amount == 汇总行 total-amount，否则 `SETTLEMENT_UNBALANCED`（detail 含差额）。
- 文件内完全相同的两行 → 第二行 `DUPLICATE_ROW`（仍保留 raw_row，不入 settlement_line）。
- 自动建/查 `store`（platform=amazon，marketplace=marketplace-name，currency）。

## 不做
- 不做匹配、利润（W3）。不调 SP-API。不做 XML/旧版 Flat File。

## 步骤
1. 先写 golden 测试：`tests/golden/amazon_v2/<样本名>.expected.json`（settlement 头、行数、按 fee_category 合计、异常列表）——期望值**从 T08 的 `expected/summary.json` 和 `anomalies.json` 推导**，不是从你的实现输出抄。
2. 实现 connector、日期/金额解析、fee_map 加载。
3. 在 pyproject 注册 entry point。
4. 测试：
   - `amazon_us_*.tsv`、`amazon_de_*.tsv` golden 相等；DE 文件某行原文 `95,00` → `Decimal("95.00")`；
   - `amazon_us_unbalanced.tsv` → 恰好 1 条 `SETTLEMENT_UNBALANCED`；
   - 未知费用 → `UNKNOWN_FEE_TYPE`，行仍入库；
   - 重复行 → `DUPLICATE_ROW`；
   - 列顺序打乱后的文件（测试里生成）结果完全相同；
   - hypothesis：随机生成平衡的结算文件，导入后 Σ settlement_line.amount == settlement.total。
5. 写 `docs/data-formats/amazon-settlement-v2.md`：支持的字段、已知取值、待验证项、来源链接。

## 涉及文件
`src/crosserp/connectors/amazon_settlement_v2/{__init__.py,connector.py,dates.py,fee_map.yaml}` `src/crosserp/core/money.py`（如需补 locale） `pyproject.toml` `tests/golden/amazon_v2/**` `tests/golden/test_amazon_v2.py` `tests/property/test_amazon_balance.py` `docs/data-formats/amazon-settlement-v2.md` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/golden/test_amazon_v2.py tests/property/test_amazon_balance.py -q` | passed |
| 三库分别 `uv run pytest -m db -k amazon -q` | passed |
| `uv run python -c "from crosserp.connectors.registry import detect; print(detect(__import__('pathlib').Path('samples/synthetic/amazon_de_2026-10-01_2026-10-14.tsv')).id)"` | `amazon.settlement_v2` |

## maken 人工验收清单
- [ ] 读 `docs/data-formats/amazon-settlement-v2.md`，看「待真实数据验证」列表，标出你的真实文件里能确认的项。
- [ ] 打开 `fee_map.yaml`，对照你在 Seller Central 见过的费用名称，告诉代理缺了哪些（如仓储费、移除费、赔偿）。
- [ ] （有真实文件时）把脱敏后的真实结算文件放进 `samples/real_anonymized/`，等 T13 完成后试导入。

## 问题

- 没有必须停下问的矛盾。店名没有单独列，导入时用 `marketplace-name`。这是推断，写在 `docs/data-formats/amazon-settlement-v2.md`。待真实数据验证。
- 未知列按任务用 `PARSE_ERROR`，severity=`info`。不另设原因码。
- 有交易行金额解析失败时，不另报 `SETTLEMENT_UNBALANCED`。差额算不准。这是推断。

## 完成记录

本地只用 SQLite。解释器是 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。`PYTHONPATH` 指向本 worktree 的 `src`。没有用 `uv run`。没有跑 MySQL / PostgreSQL。没有改 `docs/tasks/README.md`。没有推送。状态是 `review`，不是 `done`。

`detect()` 读的是已安装的 entry point。共享虚拟环境仍指向主仓库 `D:\make\write\work\CrossERP`。验收时临时把本连接器写进该环境的 `entry_points.txt`，跑完已恢复。提交里的注册在 `pyproject.toml`。

```text
pytest tests/golden/test_amazon_v2.py tests/property/test_amazon_balance.py -q
23 passed in 5.69s

pytest -m db -k amazon -q
8 passed, 118 deselected, 1 warning in 7.24s

python -c "from crosserp.connectors.registry import detect; print(detect(Path('samples/synthetic/amazon_de_2026-10-01_2026-10-14.tsv')).id)"
amazon.settlement_v2

mypy
Success: no issues found in 38 source files

pytest -q
125 passed, 1 skipped, 1 warning in 10.47s

pytest --cov=crosserp --cov-fail-under=60 -q
125 passed, 1 skipped, 1 warning in 10.16s
Required test coverage of 60% reached. Total coverage: 88.47%
```

全仓库 `ruff check .` 仍有 2 个既有问题，不在本次改动里：`src/crosserp/core/enums.py` 与 `tests/guard/test_schema_portable.py` 的全角逗号。`ruff format --check` 还指出未改动的 `src/crosserp/db/migrations/env.py`。本次新增文件的 ruff 检查通过。
