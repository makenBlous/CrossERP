# T22 报表输出：`reconcile` / `profit --out report.xlsx`

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W3 | 1 天 | T20 | `task/T22-cli-report` |

## 目标
用户两条命令拿到一个 Excel：SKU 利润表 + 异常清单（每条带中文原因），可以直接发给老板/会计看。

## 背景
- 实施方案 8 W3 第 4 条：`reconcile --period 2026-10`；`profit --period 2026-10 --out report.xlsx`（含 SKU 利润表、异常清单两个 sheet）。
- xlsx 写入用已在依赖里的 `openpyxl`（不新增依赖）。

## 范围
- `crosserp reconcile --period YYYY-MM [--store X] [--as-of YYYY-MM-DD] [--json]`：纯文本表格输出每店铺：订单类组数、已匹配、匹配率（百分比 2 位）、按原因码的未匹配数、待下期数、非订单行数、`SETTLEMENT_UNBALANCED` 数、recon_run id；`--json` 输出机器可读（金额为字符串，避免浮点）。
- `crosserp profit --period YYYY-MM [--store X] [--out report.xlsx] [--csv-dir DIR]`：
  - 没有当前 recon_run → 先自动 reconcile（打印提示）。
  - sheet「SKU利润」：列与 `profit_expected.csv` 相同顺序（期间、店铺、内部SKU、币种、销量、退款量、收入、促销、平台费、退款、采购成本、头程、广告、利润、汇率、人民币利润、备注），外加「状态」（ok/缺成本/缺汇率）、「是否全部匹配」。最后一行店铺合计（= round2(Σ 各行精确值)，不是对已舍入值求和）；「未分摊费用」单独一行。
  - sheet「异常清单」：原因码、中文名、严重度、店铺、订单号、SKU、中文说明（catalog 渲染）、建议动作、来源文件 + 行号。可按原因码筛选（Excel 自动筛选）。
  - sheet「说明」：生成时间（UTC 与 Asia/Shanghai 各一）、CrossERP 版本、`calc_version`、`inputs_hash`、recon_run id、匹配率、口径说明（**「未含广告」**、退款回库设置、非订单费用未分摊、舍入规则）。
  - 金额单元格写数值 + 格式 `#,##0.00`；值用 round2 后的 `Decimal`（openpyxl 写出为数值；精确对比请用 `--csv-dir`，CSV 里金额是字符串，与 `check-golden` 用同一序列化函数）。
  - 中文/emoji 标题在 Excel 里不乱码（openpyxl 默认 UTF-8，测试里读回校验）。
- 输出文件已存在 → 报错退出，除非 `--overwrite`。

## 不做
- 不做图表、不做 PDF、不做邮件发送。

## 步骤
1. 先写测试 `tests/integration/test_report_xlsx.py`：生成后用 openpyxl 读回，三个 sheet 存在、表头正确、合计行 = round2(Σ 精确值) 且与「Σ 已舍入值」相差不超过 0.01 × 行数、异常数 = 数据库 open issue 数、「说明」里有「未含广告」。
2. 实现 `profit/report_xlsx.py`、`profit/report_csv.py`、CLI。

## 涉及文件
`src/crosserp/profit/report_xlsx.py` `src/crosserp/profit/report_csv.py` `src/crosserp/cli.py` `tests/integration/test_report_xlsx.py` `README.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run crosserp reconcile --period 2026-10` | 表格输出，匹配率 ≥95% |
| `uv run crosserp profit --period 2026-10 --out report.xlsx` | 生成文件；再跑一次不加 `--overwrite` 报错 |
| `uv run pytest -k report_xlsx -q` | passed |

## maken 人工验收清单
- [ ] `uv run crosserp demo-import`、`uv run crosserp reconcile --period 2026-10`、`uv run crosserp profit --period 2026-10 --out D:\report.xlsx`，用 Excel/WPS 打开。
- [ ] 看三个 sheet：中文、emoji 正常；「异常清单」按原因码筛选好用；「说明」页写了「未含广告」。
- [ ] 用 Excel 自己求和「利润」列，和合计行对一下（差 0.01 以内属于舍入，说明页有解释）。

## 问题

## 完成记录
