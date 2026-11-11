# T48 AI 监控页：调用量、费用、拒答率、慢调用

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W8 | 1 天 | T47 | `main` |

## 目标
管理员/审计员能在一个页面看到：每天多少次 AI 调用、花了多少钱（估算）、被拦截比例、最慢的调用、每个用户用了多少；点开一次调用能看到它调了哪些工具。

## 背景
- 实施方案 8 W8 第 3 条、6.7 节。
- 数据来自 T44 的 `llm_call` / `llm_tool_call`；权限 `llm_monitor.read`（T35）。

## 范围
- `/llm`：时间范围（今天 / 7 天 / 30 天 / 自定义，Asia/Shanghai）；卡片：调用次数、成功/拒答/错误/超预算次数、输入/输出 token、估算费用（未配价格显示「未配置价格」）、P50/P95 耗时（后端 SQL/Python 计算，三库一致的写法）；按天折线（纯服务端生成 SVG，不引入图表库）；按用户、按模型、按渠道（cli/web/mcp/eval）表格；最慢 20 次。
- `/llm/calls/{id}`：元数据、工具调用序列、提示词版本（可展开内容）、正文（若未清理；auditor 可看，admin 可看，⚠ Q1）。
- 导出 CSV（UTF-8 BOM）。
- 提交：`main`，`feat(web): add llm monitoring page (T48)`；测试不过不提交；不发布。

## 不做
- 不做实时推送；不做告警（T49）。

## 步骤
1. 先写测试：构造固定 `llm_call` 数据 → 汇总数字精确（费用 Decimal）；P95 算法与手算一致；viewer 访问 403；三库都跑汇总查询。
2. 实现。

## 涉及文件
`src/crosserp/observability/stats.py` `src/crosserp/web/routes/{llm,__init__}.py` `src/crosserp/web/templates/{llm,llm_call}.html` `tests/unit/observability/test_stats.py` `tests/web/test_llm_page.py` `tests/web/test_permission_matrix.py`（只追加） `docs/observability.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/observability tests/web -k llm -q` | passed |
| `uv run pytest -m db -k stats -q`（三库） | passed |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 问几次问题后，管理员打开「AI 监控」：次数、费用对得上你问的次数。
- [ ] 点开最近一次：能看到它查了哪些工具。

## 问题
- Q1 按推荐默认执行：admin 和 auditor 可看尚未清理的问答正文，正文清理后显示「已清理」。

## 完成记录
- 完成内容：新增 `observability.stats` 的调用数、成功/拒答/错误、token、Decimal 费用、P50/P95 和最慢调用统计；新增 `/llm` 监控页和 `/llm/calls/{id}` 详情页；viewer 无权访问；问答正文按 Q1 推荐由 admin/auditor 查看。
- 修改文件：`src/crosserp/observability/stats.py`、`src/crosserp/web/app.py`、`src/crosserp/web/routes/__init__.py`、`src/crosserp/web/templates/{llm,llm_call}.html`、`tests/unit/observability/test_stats.py`、`tests/web/test_llm_page.py`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/pytest tests/unit/observability tests/web -k llm -q` 为 1 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 265 passed、7 skipped，覆盖率 78.61%；ruff/mypy/pre-commit 通过。
