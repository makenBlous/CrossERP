# T13 导入命令 `crosserp import` + 全样本端到端测试 + 真实文件试导入

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 1 天 | T10, T11, T12 | `task/T13-import-cli` |

## 目标
用户一条命令导入任何支持的文件；合成样本整套导入结果与标准答案一致；maken 的真实文件导入不崩溃，看不懂的东西全进异常清单。

## 背景
- 实施方案 8 W2 第 5 条和验收标准；9 节 W2 maken 任务（用真实文件试导入）。

## 范围
- CLI：`crosserp import <file>... [--type auto|amazon|shopify|mapped] [--mapping x.yaml] [--currency USD] [--store <名字>]`
  - `auto` 用 `registry.detect()`；识别不了 → 中文提示可用的 `--type`。
  - 支持一次多个文件；每个文件单独一个批次，一个失败不影响其他。
  - 输出表格：文件名、连接器、数据行数、成功行数、异常数（按原因码）、批次 id；重复文件显示「已导入过（时间），跳过」，退出码仍为 0 但打印警告；其他失败退出码 1。
- `crosserp issues list [--kind X] [--batch <id>]`：只读列出异常（W3 网页之前的最小查看方式）。
- `crosserp demo-import`：导入 `samples/synthetic/` 全部文件（按 sku_map → costs → fx → orders → 结算/打款 的顺序），供测试和 maken 使用。
- 端到端测试 `tests/integration/test_import_e2e.py`（三库）：对空库运行 demo-import → 每个文件 raw_row 数 = 文件数据行数（来自 `expected/summary.json`）；异常集合 ⊇ `anomalies.json` 中属于「导入阶段」的条目（`SETTLEMENT_UNBALANCED`、`UNKNOWN_FEE_TYPE`、`DUPLICATE_ROW`、Shopify `AMOUNT_MISMATCH`、`PARSE_ERROR`），且没有意外的额外异常；再跑一次 → 全部被判重复。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- `tests/integration/test_real_files.py`：若 `samples/real_anonymized/` 存在文件则逐个导入，断言「无未捕获异常」；目录不存在则 skip。**此目录不提交**，CI 中自动 skip。

## 不做
- 不做对账/利润/网页（W3）。

## 步骤
1. 写 CLI 命令（Typer），输出用纯文本表格（不新增依赖；若想用 rich，先问）。
2. 写 e2e 测试和真实文件测试。
3. 本地跑三库。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
4. 更新 README「快速开始」一节：`crosserp init` → `crosserp demo-import` → `crosserp issues list`。

## 涉及文件
`src/crosserp/cli.py` `src/crosserp/connectors/importer.py` `src/crosserp/db/repo/issues.py` `tests/integration/test_import_e2e.py` `tests/integration/test_real_files.py` `README.md` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run crosserp init && uv run crosserp demo-import` | 每个文件一行汇总，无报错退出 |
| 再执行 `uv run crosserp demo-import` | 每个文件显示「已导入过，跳过」 |
| `uv run crosserp issues list --kind SETTLEMENT_UNBALANCED` | 恰好 1 条 |
| 三库分别 `uv run pytest -m db -k e2e -q` | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run pytest --cov=crosserp --cov-fail-under=60` | passed |

## maken 人工验收清单
- [ ] 删除 `%USERPROFILE%\.crosserp\data.db`（如果有），运行 `uv run crosserp init`，再运行 `uv run crosserp demo-import`，截图输出。
- [ ] 运行 `uv run crosserp issues list`，对照 `samples/synthetic/EXPECTED.md`，看导入阶段的异常是不是都在。
- [ ] 把脱敏后的真实文件放进 `samples/real_anonymized/`，逐个运行 `uv run crosserp import <文件>`（领星/赛狐加 `--type mapped --mapping <你改好的yaml>`），**每个报错都截图**发给代理。
- [ ] 运行 `uv run pytest tests/integration/test_real_files.py -q`，应全部通过（不崩溃）。

## 问题

- `demo-import` 不导入 `costs.xlsx`、`fx_rates.xlsx`。它们和对应 csv 是同一份数据。两份成本都导入会因生效期重叠写出预期外的 `PARSE_ERROR`。
- 不导入 `fx_rates_missing_eur.csv`。它是缺汇率场景的替代文件，不是正常汇率表。
- 不导入 `fee_reference.csv`。没有对应导入器。留给以后的费用核对。
- 合成 Shopify 打款文件没有 `Currency` 列。`demo-import` 传入 `USD`，店铺名用 `shopify-main`，与订单表一致。这是推断。
- 本 worktree 里 Amazon 连接器仍是未跟踪文件。本次提交不包含它们，也不改 `docs/tasks/README.md`。干净检出后如果没有这些文件，Amazon 导入会失败。
- 指定解释器的 `crosserp.connectors` 入口点是空的。命令行在注册表为空时直接加载内置连接器。
- 本地只跑了 SQLite。没有跑 MySQL / PostgreSQL。没有删除用户目录里的 `data.db`。验收用的是临时 SQLite 文件。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 完成记录

本地只用 SQLite。解释器是 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。`PYTHONPATH` 指向本 worktree 的 `src`。没有用 `uv run`。没有跑 MySQL / PostgreSQL。任务验收命令里的 `uv run` 按上面的解释器替换。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

```text
pytest -m db -k e2e -q
3 passed, 173 deselected, 1 warning in 2.52s

pytest tests/integration/test_real_files.py -q
1 skipped in 0.61s
samples/real_anonymized/ 不存在

pytest --cov=crosserp --cov-fail-under=60 -q
174 passed, 2 skipped, 1 warning in 18.30s
Total coverage: 86.01%

mypy
Success: no issues found in 48 source files
```

临时 SQLite 上 `init`、`demo-import`、再跑一次 `demo-import`、`issues list --kind SETTLEMENT_UNBALANCED` 都退出码 0。第一次每个文件一行。第二次每个文件显示「已导入过（时间），跳过」。`SETTLEMENT_UNBALANCED` 恰好 1 条。导入阶段异常共 4 条：`DUPLICATE_ROW`、`UNKNOWN_FEE_TYPE`、`SETTLEMENT_UNBALANCED`、Shopify `AMOUNT_MISMATCH`。没有额外异常。

`ruff check .` 仍有 2 个既有问题，在 `enums.py` 和 `tests/guard/test_schema_portable.py`。本次文件已通过 ruff。未改 `docs/tasks/README.md`。未改审计哈希规则。未推送。
