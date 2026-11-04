# T54 质量门槛提高：覆盖率 80%、mypy 覆盖新模块（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W10 | 1.5 天 | T53 | `main` |

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
- **Q1 ⚠ 待 maken 确认：覆盖率门槛。** 选项：A 80%（实施方案目标，推荐）；B 75%（如果 AI/MCP 部分难测）；C 分包门槛（核心金额相关包 90%，其他 70%）。

## 完成记录
（代理填写）
