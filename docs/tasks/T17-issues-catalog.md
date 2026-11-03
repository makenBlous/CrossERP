# T17 异常目录：原因码枚举定稿 + 中文模板 + 候选码落地

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W3 | 0.5 天 | T14 | `task/T17-issues-catalog` |

## 目标
所有原因码有唯一来源（枚举 + `catalog.yaml`），每条异常都能渲染成一句中文人话；T14 的 5 个候选码按 maken 的决定进枚举。

## 背景
- 实施方案 6.1（13 个原因码）、8 W3 第 3 条（issues/：原因码枚举 + 中文模板）。
- T14 产出 `docs/rules/recon-categories.md` 和 `src/crosserp/issues/catalog_draft.yaml`；候选码 `FEE_OVERCHARGE`、`SETTLEMENT_DELAYED`（「待下期」）、`CHARGEBACK`、`PARTIAL_REFUND`、`DUPLICATE_SETTLEMENT` **仍待 maken 确认**。

## 开工前检查（必须）
打开 `docs/rules/recon-categories.md` 的「开放问题清单」，看 maken 对 5 个候选码的勾选：
- 已勾「要」→ 进枚举；已勾「不要」→ 不进，T19 对应规则跳过；
- **没勾**→ 状态改 `blocked`，在「问题」一节列出未决的码，等 maken。不要自己决定。

## 范围
- `core/enums.py` 的 `IssueKind`：6.1 的 13 个 + maken 确认的候选码。数据库列是 `String(32)`，加码**不需要迁移**。
- `src/crosserp/issues/catalog.yaml`（由 `catalog_draft.yaml` 改名定稿；draft 文件删除）每个码：
  `kind`、`name_zh`、`severity`（info/warn/error）、`counts_as_unmatched`（是否算未匹配，影响指标 2）、`template_zh`（Python `str.format` 占位符，如 `订单 {order_id} 的 SKU {sku} 结算数量 {settle_qty}，订单表 {order_qty}`）、`action_zh`（建议怎么处理）。
- `issues/catalog.py`：启动时加载并校验——枚举和 yaml **一一对应**（多一个少一个都报错）；`render(issue) -> str`（占位符缺失时不崩，显示 `{缺:order_id}` 并记日志）。
- `issues/service.py`：`open_issue(session, kind, *, store_id, period, source_ref, detail) -> Issue`，统一写 `issue` 表（`status=open`），同一 `(kind, source_ref)` 在同一次对账运行里不重复开。现有导入阶段直接写 `issue` 的地方改为调用它（PR 里列出改了哪些）。
- 依赖：读 yaml 需要 YAML 库——若 T14 时 maken 已同意 `pyyaml` 就用它；否则改用 `catalog.toml` + 标准库 `tomllib`（Python ≥3.11 自带），**不新增依赖**。

## 不做
- 不做异常状态流转（explained/resolved/ignored 的界面和命令是 W5）。
- 不做 AI 解释。

## 步骤
1. 先写测试 `tests/unit/test_issue_catalog.py`：枚举与目录一一对应；每个模板用 T08 `anomalies.json` 里对应场景的 detail 渲染不报错、不含 `{缺:`；`counts_as_unmatched=True` 的集合 = {NOT_IN_ERP, REFUND_WITHOUT_ORDER, QTY_MISMATCH, AMOUNT_MISMATCH, SKU_UNMAPPED, CURRENCY_MISMATCH}（推断：与 6.2 伪代码里会让组「未匹配」的分支一致；`CURRENCY_MISMATCH` 是否算，PR 里请 maken 确认）。
2. 实现 catalog / service，替换旧写法。
3. `crosserp issues list` 输出改为显示中文 `name_zh` + 渲染后的句子。

## 涉及文件
`src/crosserp/core/enums.py` `src/crosserp/issues/catalog.yaml`（或 `.toml`） `src/crosserp/issues/catalog.py` `src/crosserp/issues/service.py` `src/crosserp/connectors/importer.py` `src/crosserp/cli.py` `tests/unit/test_issue_catalog.py` `docs/rules/recon-categories.md`（只把「候选」改为「已确认/已否决」）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/test_issue_catalog.py -q` | passed |
| `uv run crosserp demo-import && uv run crosserp issues list` | 每条一行中文句子，没有 `{缺:` |
| `uv run pytest -m db -k e2e -q`（三库） | passed（T13 行为不变） |

## maken 人工验收清单
- [ ] 开工前：在 `docs/rules/recon-categories.md` 把 5 个候选码逐个勾「要/不要」。
- [ ] 运行 `uv run crosserp issues list`，随便挑 5 条读一遍，看中文是不是你能看懂、建议动作是不是对的。不顺的句子直接改 `catalog.yaml` 里的文字（改文字不用写代码）。

## 问题

## 完成记录
