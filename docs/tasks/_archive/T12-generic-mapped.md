# T12 通用映射导入器：领星 / 赛狐 / 成本表 / 汇率表 / SKU 映射

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 1.5 天 | T09（样本来自 T08） | `task/T12-generic-mapped` |

## 目标
不写死任何 ERP 的列名，靠 YAML 把任意 xlsx/csv 映射成订单、成本、汇率、SKU 映射，真实表头到手后只改 YAML 不改代码。

## 背景
- 实施方案 5.3（领星，待真实数据验证）、5.4（赛狐，待真实数据验证）、5.5（成本/汇率模板列）、8 W2 第 3 条。

## 范围
- `connectors/generic_mapped/connector.py`，`id = "generic.mapped"`，`sniff()` 恒为 0（必须显式 `--type mapped --mapping x.yaml`）。
- 读取：`.xlsx` 用 python-calamine（指定 sheet，默认第一个；跳过前 N 行可配置），`.csv` 用 csv 模块（编码可配置，默认 `utf-8-sig`，可选 `gb18030`——领星/赛狐导出编码未核实）。
- YAML 结构（写 Pydantic 模型校验，并生成 `docs/data-formats/mapping-yaml.md`）：
```yaml
target: order_line            # order_line | sku_cost | fx_rate | sku
source_name: lingxing_orders  # 写入 provenance
sheet: 0
header_row: 1
encoding: utf-8-sig
amount_locale: us
date_formats: ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
timezone: Asia/Shanghai       # 源文件时间所在时区，转 UTC
columns:                      # 我们的字段: 源文件表头名
  platform_order_id: "TODO_订单号"
  platform_sku: "TODO_MSKU"
  qty: "TODO_数量"
  order_date: "TODO_订购时间"
  item_price: "TODO_商品金额"
  currency: "TODO_币种"
defaults:
  store: "amazon-us"
```
- 必填字段缺映射或表头找不到 → 整批失败，提示「YAML 里的 X 对应的表头 Y 在文件里不存在，文件实际表头是 …」。
- 提供：`mappings/lingxing_orders.yaml`、`mappings/sellfox_orders.yaml`（列名全部 `TODO_` 前缀，注明待真实文件确认）；`mappings/template_costs.yaml`、`mappings/template_fx_rates.yaml`（对应 5.5 模板列）；合成样本用的 `samples/synthetic/mappings/synthetic_orders.yaml` 来自 T08。
- 生成 `samples/templates/costs.xlsx`、`fx_rates.xlsx` 空模板（表头 + 1 行示例）。
- `sku_cost` 生效期重叠 → `PARSE_ERROR`（detail 写明冲突的两段）；`fx_rate` 用 upsert（同月同币对覆盖并写审计）。

## 不做
- 不做 AI 列映射建议（v0.5）；不调领星/赛狐 API。

## 步骤
1. 写 mapping 模型与加载、读取器、标准化。
2. 测试：合成 orders.csv / costs.csv / costs.xlsx / fx_rates.xlsx / sku_map.csv 导入行数正确；表头不存在时报错信息包含实际表头；`TODO_` 未改的 YAML 被拒绝并提示「请先填写真实表头」；生效期重叠被报出；xlsx 与 csv 导入结果相同。
3. 文档。

## 涉及文件
`src/crosserp/connectors/generic_mapped/**` `src/crosserp/connectors/mappings/*.yaml` `samples/templates/*.xlsx` `tests/golden/test_generic_mapped.py` `docs/data-formats/mapping-yaml.md` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/golden/test_generic_mapped.py -q` | passed |
| 三库分别 `uv run pytest -m db -k mapped -q` | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## maken 人工验收清单
- [ ] 打开 `src/crosserp/connectors/mappings/lingxing_orders.yaml`，把 `TODO_` 后面的字换成你领星导出文件里**真实的表头名**（只改右边），保存。赛狐同理。
- [ ] 用 Excel 打开 `samples/templates/costs.xlsx`，确认这几列你都能填：内部SKU、采购单价、头程单价、币种、生效日期。
- [ ] 如果你的导出文件是 GBK/GB18030 编码（Excel 打开中文正常、记事本打开乱码），告诉代理。

## 问题

- 领星/赛狐列名仍是 `TODO_`。待真实导出后再改 YAML。没有编造字段全集。
- 成本生效期按 `[开始, 结束)`。未填结束日时接到同一 SKU 的下一条。不含下一条当天。这是推断。与 `scripts/gen_samples.py` 的注释一致。若结束日要含当天，需要 maken 决定。
- T09 的标准记录没有 SKU。本次补了 `SkuRec` 和落库。没有改表。没有改 `audit/chain.py`。
- 同月同币对覆盖会另写 `fx_rate_upsert` 审计。同一 sha256 仍不能重导。覆盖要用另一份文件。

## 完成记录

本地只用 SQLite。解释器是 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。`PYTHONPATH` 指向本 worktree 的 `src`。没有用 `uv run`。没有跑 MySQL / PostgreSQL。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

任务验收命令里的 `uv run` 按上面的解释器替换。

```text
pytest tests/golden/test_generic_mapped.py -q
15 passed in 2.68s

pytest -m db -k mapped -q
15 passed, 103 deselected, 1 warning in 3.43s

mypy
Success: no issues found in 41 source files

pytest -q
117 passed, 1 skipped, 1 warning in 6.64s
```

改动文件的 `ruff format --check` 与 `ruff check` 通过。仓库里原有的 `src/crosserp/db/migrations/env.py` 格式差异，以及 `enums.py` / `test_schema_portable.py` 的全角逗号，不是这次引入的。没有改。

额外改了这些文件。原因：不改就写不进 `sku` 表，汇率也不能覆盖。

- `src/crosserp/core/models.py`：增加 `SkuRec`。`Provenance` 增加可空 `source_name`。`ColumnMapping` 增加 `skip_rows`。
- `src/crosserp/connectors/importer.py`：SKU 落库。汇率 upsert 并写审计。成本与已有生效期冲突时记 `PARSE_ERROR`。
- `src/crosserp/db/repo/imports.py`：增加 `insert_sku`。
- `pyproject.toml`：只在 `crosserp.connectors` 注册 `mapped`。
- `docs/architecture.md`：标准记录补上 SKU 映射。

未改 `docs/tasks/README.md`。未加 `crosserp import`。那是 T13。
