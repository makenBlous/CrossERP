# CrossERP

跨境电商对账、SKU 利润与审批记账工具（v0.1 开发中）。

当前可以导入 Amazon 结算报告、Shopify 打款 CSV，以及带 YAML 列映射的订单、成本、汇率和 SKU。对账、利润和网页报表还没做。

## 快速开始

快速体验（使用独立的演示数据库）：

```bash
uv sync
uv run crosserp demo --check --no-browser
uv run crosserp demo --no-browser
```

正式库操作仍可使用 `uv run crosserp init`。演示数据来自包内固定样本，不会写入正式数据库。

`init` 会在本机创建 SQLite 数据库。默认路径是 `%USERPROFILE%\.crosserp\data.db`。要换 MySQL 或 PostgreSQL，只改配置文件里的 `CROSSERP_DATABASE_URL`，不改代码。

`demo-import` 按 sku 映射、成本、汇率、订单、结算/打款的顺序导入 `samples/synthetic/`。再跑一次会提示每个文件已导入过，并跳过。

导入自己的文件：

```bash
uv run crosserp import path/to/settlement.tsv
uv run crosserp import path/to/orders.xlsx --type mapped --mapping path/to/mapping.yaml
uv run crosserp import path/to/payout.csv --type shopify --currency USD --store shopify-main
uv run crosserp issues list --kind SETTLEMENT_UNBALANCED
```

`--type` 可以是 `auto`、`amazon`、`shopify`、`mapped`。识别不了时会提示改用这几个值。一次可以传多个文件。每个文件单独一个批次。重复文件退出码是 0。其他失败退出码是 1，并且不会挡住其余文件。
