# T12 通用映射导入器：领星 / 赛狐 / 成本表 / 汇率表 / SKU 映射

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W2 | 1.5 天 | T09（样本来自 T08） | `task/T12-generic-mapped` |

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
| 三库分别 `uv run pytest -m db -k mapped -q` | passed |

## maken 人工验收清单
- [ ] 打开 `src/crosserp/connectors/mappings/lingxing_orders.yaml`，把 `TODO_` 后面的字换成你领星导出文件里**真实的表头名**（只改右边），保存。赛狐同理。
- [ ] 用 Excel 打开 `samples/templates/costs.xlsx`，确认这几列你都能填：内部SKU、采购单价、头程单价、币种、生效日期。
- [ ] 如果你的导出文件是 GBK/GB18030 编码（Excel 打开中文正常、记事本打开乱码），告诉代理。

## 问题

## 完成记录
