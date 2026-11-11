# T51 评测记录入库 + 基线对比 + CI 离线评测（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W9 | 1 天 | T50 | `main` |

## 目标
每次评测结果存进数据库，并和 `tests/eval/baseline.json` 对比：分数下降就失败。CI 每次都用离线回放跑一遍；真实模型评测只能手动触发。

## 背景
- 实施方案 8 W9 第 2 条。
- 下一个迁移号 **0017**。
- CI 现状：`.github/workflows/ci.yml` 有 install-smoke（3 系统）、lint、test（覆盖率 60）、db-matrix；远程 CI 是否全绿**未核实**（T16 记录过 CI #2 全部失败：https://github.com/makenBlous/CrossERP/actions/runs/41567272614 ）。
- 仓库可能是公开的（**推断**，依据：T16 通过公开 API 看到了 Actions 结果）。v1.0 前不发布的决定与「公开仓库 + 每次 push 跑 CI」需要一起考虑，见 Q1。

## 范围
- 迁移 `0017_eval_run`：`eval_run`（`id`、`ts`、`model`、`prompt_version_id`、`git_sha String(40)`、`total Integer`、`passed Integer`、`details_json JSON`、`triggered_by String(64)`）。
- `crosserp eval run --save` 入库；`crosserp eval compare --baseline tests/eval/baseline.json`：任一题由过变不过或总分下降 → 退出码 1，打印中文差异。
- `crosserp eval baseline --update`：只能 maken 手动执行并提交（更新基线算「修改」，提交信息必须写原因）。
- CI：`ci.yml` 新增 job `eval-offline`（`crosserp eval run --model test` + `compare`）；新增 `.github/workflows/eval-model.yml`，仅 `workflow_dispatch`，从仓库 secret 读 key（secret 由 maken 自己配，代理不碰）。
- 提交：`main`，`feat(evals): store eval runs and gate on baseline (T51)`；测试不过不提交；不发布。

- 新增验收项 F：测试里用一份「故意改坏」的提示词副本跑离线评测，断言 compare 判失败（不修改正式提示词）。

## 不做
- 不做定时评测；不做评测网页（监控页可加一栏，可选）。

## 步骤
1. 测试：入库字段正确；compare 三种情况（持平、提升、下降）；三库迁移。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
2. 本地用 `act` 或直接按 job 命令跑一遍 eval-offline（无 PowerShell/Windows 环境的部分标「未在本机验证」）。

## 涉及文件
`src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0017_eval_run.py` `src/crosserp/evals/run.py` `tests/eval/baseline.json` `src/crosserp/cli.py` `.github/workflows/{ci.yml,eval-model.yml}` `scripts/sql/grant_*.sql` `tests/unit/evals/test_compare.py` `tests/integration/test_eval_run_db.py` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run crosserp eval run --model test --save && uv run crosserp eval compare --baseline tests/eval/baseline.json` | 退出码 0 |
| 人为改坏一个回放答案后 compare | 退出码 1，指出哪题（测试里做，不提交坏数据） |
| `uv run pytest -m db -k "eval or migration" -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 如需在 GitHub 上跑真实模型评测：仓库 Settings → Secrets 里自己添加 `CROSSERP_API_KEY` 等（不要发给代理），再在 Actions 页面手动点「Run workflow」。
- [ ] 看 CI 页面：`eval-offline` 是绿色。

## 问题
- Q1 maken 已选择 B：保持公开并继续 push 跑 CI；本任务只提交 CI 配置，不执行 GitHub 发布、tag 或 Release 动作。真实模型仍仅 workflow_dispatch。
- Q1 已按 maken 决定 B：保持 GitHub 仓库公开并继续 push 跑 CI；本任务不执行发布、tag 或 Release。
- Q2 按推荐默认：真实模型评测只允许 `workflow_dispatch` 手动触发，不放入 push CI。

## 完成记录
- 完成内容：按推荐默认实现评测结果入库、离线基线比较、缺失题目回归检测、`eval run --save`，以及 push CI 离线评测和仅手动触发的真实模型工作流。
- 修改文件：`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0017_eval_run.py`、`src/crosserp/evals/run.py`、`src/crosserp/cli.py`、`tests/eval/baseline.json`、`.github/workflows/ci.yml`、`.github/workflows/eval-model.yml`、`tests/unit/evals/test_compare.py`、`tests/integration/test_eval_run_db.py`、`tests/integration/test_migrations.py`、`tests/guard/test_schema_portable.py`、`CHANGELOG.md`。
- 测试结果：`eval run --model test --save` 后 `eval compare` 通过（20/20）；ruff format/check、mypy 全部通过；T51 相关测试 17 passed；全量 `pytest -q --cov=crosserp --cov-fail-under=60` 为 273 passed、7 skipped，覆盖率 78.69%；MySQL/ PostgreSQL 本地未运行（当前环境未提供数据库服务）。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 偏离计划：原验收命令中的 `--save` 尚未落地，已补齐并增加 SQLite 入库集成测试；评测计数列 `total`/`passed` 按任务定义保持 Integer，并补充守卫例外。
