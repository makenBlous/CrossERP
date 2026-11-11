# T17 异常目录：原因码枚举定稿 + 中文模板 + 候选码落地

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 0.5 天 | T14 | `task/T17-issues-catalog` |

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
| `uv run pytest -m db -k e2e -q`（三库） | passed（T13 行为不变） |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## maken 人工验收清单
- [ ] 开工前：在 `docs/rules/recon-categories.md` 把 5 个候选码逐个勾「要/不要」。
- [ ] 运行 `uv run crosserp issues list`，随便挑 5 条读一遍，看中文是不是你能看懂、建议动作是不是对的。不顺的句子直接改 `catalog.yaml` 里的文字（改文字不用写代码）。

## 问题

## 完成记录

分支：`task/T17-issues-catalog`。状态改为 `review`，不是 `done`。

### 做了什么

- 将 `catalog_draft.yaml` 定稿为 `src/crosserp/issues/catalog.yaml`，补齐 `kind`、`name_zh`、`severity`、`counts_as_unmatched`、`template_zh`、`action_zh`，并删除草稿文件。
- 新增 `issues/catalog.py`：启动时校验目录与 `IssueKind` 一一对应；缺少模板字段时显示 `{缺:字段}` 并记录 warning，不抛出渲染异常。
- 新增 `issues/service.py`：`open_issue` 统一原因码、严重度、open 状态和同一 `source_ref` 去重。
- 导入阶段的 `PARSE_ERROR`、连接器产生的 `IssueRec` 改为经过 `open_issue`；`crosserp issues list` 显示中文名称和渲染后的说明。
- 在规则文档中记录 maken 已确认的五个候选码及相关口径：五码全部启用，币种不一致计入未匹配，不平衡结算单不继续匹配明细等。

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/unit/test_issue_catalog.py -q` | 6 passed |
| `uv run pytest tests/integration/test_issue_catalog_service.py -q` | 1 passed |
| `uv run pytest -m db -k e2e -q` | SQLite 3 passed |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 uv run pytest -m db -k e2e -q` | MySQL 3 passed |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp uv run pytest -m db -k e2e -q` | PostgreSQL 3 passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run crosserp demo-import && uv run crosserp issues list` | 已实际验证 `SETTLEMENT_UNBALANCED` 显示中文名称和完整说明 |
| `uv run pytest --cov=crosserp --cov-fail-under=60 -q` | 186 passed, 2 skipped；覆盖率 85.53% |
| `uv run mypy` | 0 errors |
| `uv run ruff format --check . && uv run ruff check .` | 全部通过 |

### 偏离计划

- 未新增依赖，继续使用项目已有的 PyYAML。
- 未实现异常状态流转或 AI 解释；只完成目录、渲染和导入阶段统一写入。
