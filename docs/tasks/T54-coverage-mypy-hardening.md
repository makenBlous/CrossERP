# T54 质量门槛提高：覆盖率 80%、mypy 覆盖新模块（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W10 | 1.5 天 | T53 | `main` |

## 目标
CI 的覆盖率门槛从 60% 提到 80%；mypy 严格检查覆盖 W5–W9 新增的所有包；为此补测试，不删任何测试、不加 `# pragma: no cover` 绕过（确需排除的写原因）。

## 背景
- 仓库现状：`ci.yml` 中 `--cov-fail-under=60`；W4 结束时实测覆盖率 84.70%（W4 证据）；AGENTS.md §4 列了 mypy 检查的包（不含 auth/agent/observability/mcp_server/vouchers，这些目录 AGENTS §3 原本禁止创建）。
- 红线：测试只加不删。

## 范围
- `ci.yml` 与 `pyproject.toml`：`fail_under = 80`（⚠ Q1）。
- mypy 配置加入：`crosserp.auth`、`crosserp.vouchers`、`crosserp.agent`、`crosserp.observability`、`crosserp.mcp_server`、`crosserp.config`、`crosserp.web`；第三方无类型库用 `ignore_missing_imports` 精确到模块。
- 补测试到 80%（优先：错误分支、权限 403 分支、迁移降级）。
- 列出所有 `pragma: no cover` 与 `type: ignore`，每处带原因。
- 提交：`main`，`test: raise coverage gate to 80 and extend mypy (T54)`；测试不过不提交；不发布。

## 不做
- 不重构业务代码（除非为可测性需要的小改动，需在完成记录说明）。

## 涉及文件
`.github/workflows/ci.yml` `pyproject.toml` `tests/**`（只增） `AGENTS.md`（§4 mypy 列表，见 AGENTS 修改段落） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest --cov=crosserp --cov-fail-under=80 -q` | passed，覆盖率 ≥ 80% |
| `uv run mypy src` | 0 错误 |
| `git diff --stat HEAD~1 -- tests` | 只有新增/修改，无删除的测试函数（完成记录附统计） |

## maken 人工验收清单
- [ ] 看完成记录里的覆盖率数字（≥ 80）和「测试数前后对比」：测试只多不少。

## 问题
- Q1 按推荐默认：覆盖率门槛提高到 80%。

## 完成记录
- 完成内容：CI 覆盖率门槛从 60% 提高到 80%，`pyproject.toml` 固定 `fail_under = 80`；补充小模块错误分支、只读工具、token 生命周期、checkpoint、CSV 输出和 MCP 白名单测试。
- 测试数量：T54 新增 8 个测试；全量回归 278 → 286 个测试（只增加，不删除测试函数）。
- 实际结果：全量 SQLite `pytest --cov=crosserp --cov-fail-under=80 -q` 为 286 passed、7 skipped，覆盖率 80.10%；`mypy src` 0 错误；ruff、pre-commit 通过。
- `pragma: no cover`：全仓库没有此标记。
- `type: ignore` 清单与原因：`tests/golden/test_amazon_v2.py`、`tests/unit/test_import_models.py`、`tests/unit/test_money.py`、`tests/integration/test_db_types.py` 的 ignore 只用于故意传入错误类型的运行时守卫测试；`src/crosserp/audit/export.py` 是 SQLAlchemy 行类型收窄；`src/crosserp/mcp_server/server.py` 是 mcp 运行时可选 API；`src/crosserp/observability/prices.py`、`src/crosserp/evals/run.py`、`src/crosserp/vouchers/accounts.py`、`src/crosserp/issues/catalog.py`、`src/crosserp/connectors/{amazon_settlement_v2/connector.py,shopify_payouts/connector.py,generic_mapped/mapping.py}`、`src/crosserp/ledger/targets/{generic_xlsx.py,kingdee_xlsx.py}`、`src/crosserp/profit/report_xlsx.py` 是第三方 YAML/openpyxl 库没有完整类型声明；`src/crosserp/cli.py` 是 mcp server 的动态 `stdio` 方法。没有用 ignore 绕过业务类型错误。
