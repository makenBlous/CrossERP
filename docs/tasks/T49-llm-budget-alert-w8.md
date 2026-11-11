# T49 AI 预算与告警：超额横幅 + 硬拒绝 + 演示脚本 + W8 验收证据（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W8 | 1.5 天 | T48 | `main` |

## 目标
管理员设一个每月 AI 预算；用到 80% 时页面顶部出现黄色提醒，用满 100% 后新的提问被直接拒绝（不调用模型），并说明原因；整理 W8 验收证据和一份可照着演示的脚本。

## 背景
- 实施方案 8 W8 第 4、5 条与 W8 验收。
- 费用来自 T44 `cost_estimate`（估算）；未配价格的调用按 token 预算计（Q1）。
- 下一个迁移号 **0016**。

## 范围
- 迁移 `0016_llm_budget`：`llm_budget`（`id`、`scope String(16)`=global/user、`user_id NULL`、`period String(7)`、`limit_amount Money4 NULL`、`limit_tokens BigInteger NULL`、`currency`、`warn_percent Integer` 默认 80、`created_by`、`created_at`）；`llm_alert`（`id`、`ts`、`budget_id`、`kind`=warn/block、`used_amount`、`used_tokens`、`acknowledged_by NULL`、`acknowledged_at NULL`）。
- `observability/budget.py`：`check(session, user) -> ok|warn|block`（调用前检查；用量 = 本月 `llm_call` 汇总，Decimal）；首次跨过阈值时写 `llm_alert`；block 时 `llm_call.status=budget_blocked`，不发请求。
- 网页：`/settings/budget`（`budget.manage`）；所有页面 `base.html` 顶部横幅（warn 黄、block 红），admin 可点「知道了」确认（写 acknowledged）。CLI `crosserp ai budget set|show`。
- 设置/修改预算写业务审计。
- `docs/demo_flow.md`：从 `crosserp init` 到导入、对账、异常处理、凭证审批下载、AI 问答、MCP、监控、审计导出的 15 分钟演示脚本，每步给 PowerShell 命令与预期画面。
- W8 证据 `docs/evidence/W8.md`（截图位待 maken 补）。
- 提交：`main`，`feat(observability): add llm budget and alerts (T49)`；证据与演示脚本 `docs: add W8 evidence and demo flow (T49)`；测试不过不提交；不发布。

## 不做
- 不发邮件/飞书（第 3 月）；不做按部门预算。

## 步骤
1. 先写测试：用量 79% → ok；80% → warn 且只写一条 alert；100% → block 且未调用模型（`FunctionModel` 调用计数为 0）；月份切换后重置；预算未设置 → 不限制；并发两请求跨阈值只一条 alert（三库）。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
2. 迁移（三库升级/降级）→ 实现 → 文档。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
3. 按 `docs/demo_flow.md` 完整跑一遍（离线模型），记录结果。

## 涉及文件
`src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0016_llm_budget.py` `src/crosserp/observability/budget.py` `src/crosserp/agent/runtime.py` `src/crosserp/mcp_server/server.py` `src/crosserp/web/routes/{budget,__init__}.py` `src/crosserp/web/templates/{base,budget}.html` `src/crosserp/cli.py` `scripts/sql/grant_*.sql` `tests/unit/observability/test_budget.py` `tests/integration/test_budget_db.py` `docs/demo_flow.md` `docs/evidence/W8.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/observability -q` | passed |
| `uv run pytest -m db -k "budget or migration or grants" -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 管理员在「AI 预算」设本月 1 元（或 1000 token）。
- [ ] 问几次直到超额：先看到黄色提醒，再看到红色「本月预算已用完」，再问被拒绝。
- [ ] 照 `docs/demo_flow.md` 从头演示一遍，哪一步卡住就记在 W8.md 里。

## 问题
- Q1、Q2 按推荐默认执行：金额优先、无价格时 token 兜底；超额后 admin 也不能继续使用，必须调整预算并留痕。

## 完成记录
- 完成内容：新增 0016 `llm_budget`/`llm_alert` 表、金额优先/ token 兜底检查、warn/block 阈值告警和 CLI `ai budget-set`；按推荐执行 admin 不豁免。
- 测试结果：预算单元/迁移 7 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 267 passed、7 skipped，覆盖率 78.66%；ruff/mypy/pre-commit 通过。
