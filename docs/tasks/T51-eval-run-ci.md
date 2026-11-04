# T51 评测记录入库 + 基线对比 + CI 离线评测（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W9 | 1 天 | T50 | `main` |

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
1. 测试：入库字段正确；compare 三种情况（持平、提升、下降）；三库迁移。
2. 本地用 `act` 或直接按 job 命令跑一遍 eval-offline（无 PowerShell/Windows 环境的部分标「未在本机验证」）。

## 涉及文件
`src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0017_eval_run.py` `src/crosserp/evals/run.py` `tests/eval/baseline.json` `src/crosserp/cli.py` `.github/workflows/{ci.yml,eval-model.yml}` `scripts/sql/grant_*.sql` `tests/unit/evals/test_compare.py` `tests/integration/test_eval_run_db.py` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run crosserp eval run --model test --save && uv run crosserp eval compare --baseline tests/eval/baseline.json` | 退出码 0 |
| 人为改坏一个回放答案后 compare | 退出码 1，指出哪题（测试里做，不提交坏数据） |
| `uv run pytest -m db -k "eval or migration" -q`（三库） | passed |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 如需在 GitHub 上跑真实模型评测：仓库 Settings → Secrets 里自己添加 `CROSSERP_API_KEY` 等（不要发给代理），再在 Actions 页面手动点「Run workflow」。
- [ ] 看 CI 页面：`eval-offline` 是绿色。

## 问题
- **Q1 ⚠ 待 maken 确认：仓库可见性与 CI（与「v1.0 前不发布」相关）。** 选项：A 把 GitHub 仓库改为私有，继续 push 跑 CI（推荐；私有仓库 Actions 有免费额度限制，额度数字「未核实」以 GitHub 官方为准）；B 保持公开（等于提前公开源码，与「不推公开仓库」的决定冲突）；C 不再 push，CI 只在本地按 job 命令跑；D 推到私有镜像仓库跑 CI。
- **Q2 ⚠ 待 maken 确认：真实模型评测是否放 CI。** 选项：A 只 `workflow_dispatch` 手动（推荐）；B 不放 CI，只本机跑。

## 完成记录
（代理填写）
