# T42 AI 只读工具层 `agent/tools.py`（只读账号）+ 规则文档检索（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W7 | 1.5 天 | T41 | `main` |

## 目标
给 AI 准备一组「只能查、不能改」的工具：查订单、查利润、查异常、查对账结果、查审批状态、搜规则文档。工具只通过只读数据库账号连接；每个工具返回的数字都带「来源行」引用，后面的回答必须引用它们。

## 背景
- 实施方案 8 W7 第 1 条；0 节红线「AI 不算钱」：AI 只能**读取**系统已算好的金额，任何加减乘除都由工具（确定性代码）完成。
- 仓库现状：T30 已有 `db/session.get_agent_database_url()`（环境变量 `CROSSERP_AGENT_DATABASE_URL`）和 `readonly_session`；grants 脚本给 agent 账号只 SELECT 业务表；T32 已确保 agent 读不到用户/会话/token 表。
- 依赖：`pydantic-ai`（PyPI 2.66.0，2026-11-04 查，见 prep_notes），当前 `uv.lock` 没有，见 Q1。本任务只用其 `Tool`/`RunContext` 类型，不调模型。

## 范围
- `src/crosserp/agent/tools.py`：每个工具是普通函数 + Pydantic 输入/输出模型，输入有上限（日期跨度 ≤ 366 天、返回行数 ≤ 200）：
  - `get_profit(store, period)`、`list_issues(status, kind, store, limit)`、`get_order(order_no)`、`get_settlement(settlement_id)`、`get_recon_summary(run_id|store+period)`、`get_approval_status(target_type, target_id)`、`get_voucher(voucher_id)`、`compare_profit(store, period_a, period_b)`（差额由代码算好返回）、`search_rules_doc(query, k=5)`。
  - 输出统一结构：`{"data": ..., "citations": [{"table": "profit_snapshot", "id": "...", "field": "net_profit", "value": "123.45"}]}`；金额一律字符串化 Decimal。
- `search_rules_doc`：只索引仓库内 `docs/rules/*.md`（仓库已有 `docs/rules/recon-categories.md`；平台费用规则等新文档由 maken 提供），用简单 BM25/关键词（纯 Python，无向量库，⚠ Q2），返回段落 + 文件名 + 行号作为引用。
- `agent/db.py`：工具只能拿到 `readonly_session`；构造时若 `CROSSERP_AGENT_DATABASE_URL` 未设置：SQLite 下用只读 URI（`mode=ro`），PG/MySQL 下拒绝启动 AI 并提示（不回退到主账号）。
- 守卫测试 `tests/guard/test_agent_readonly.py`：`agent/` 不得 import `ledger`、`approval.service` 的写函数、`db.repo.*` 的写函数（AST 检查）；三库下用 agent 账号执行 INSERT 失败。
- 提交：`main`，`feat(agent): add read-only tools with citations (T42)`；测试不过不提交；不发布。

## 不做
- 不接模型、不做问答（T43）；不做向量检索。

## 步骤
1. 先写测试：每个工具 demo 数据下返回值与直接查表一致（金额逐分相等）；citations 指向真实存在的行；超上限参数报错；`compare_profit` 差额与 `profit` 模块结果一致；agent 账号写入被拒（三库）。
2. 实现工具 → 文档检索 → 守卫。

## 涉及文件
`pyproject.toml` `uv.lock` `src/crosserp/agent/{__init__,tools,db,rules_search}.py` `tests/unit/agent/test_tools.py` `tests/guard/test_agent_readonly.py` `tests/integration/test_agent_grants.py` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/agent tests/guard -q` | passed |
| `uv run pytest -m db -k agent -q`（三库） | passed |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 把你手上的平台费用规则（如佣金比例说明）整理成一两份 Markdown 放到 `docs/rules/`（不要放账号密码）。
- [ ] 看完成记录里代理贴的「工具清单」，确认没有任何一个是「修改」「删除」「导出」类。

## 问题
- **Q1 ⚠ 待 maken 确认：新增依赖 pydantic-ai。** 选项：A 加 `pydantic-ai-slim`（只装核心 + OpenAI 兼容客户端，体积小，推荐）；B 加完整 `pydantic-ai`；C 不用框架，自己写 OpenAI 兼容调用（代码多、维护重）。版本以加入当天 PyPI 为准（2026-11-04 为 2.66.0）。AGENTS.md §2 写的 2.64 需同步更新（见 AGENTS 修改段落）。
- **Q2 ⚠ 待 maken 确认：规则文档检索方式。** 选项：A 纯 Python 关键词/BM25（推荐，零依赖、可解释）；B 向量检索（需要嵌入模型与额外依赖）。

## 完成记录
（代理填写）
