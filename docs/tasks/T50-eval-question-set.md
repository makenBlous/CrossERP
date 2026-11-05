# T50 AI 评测集：20 个问题 + pydantic-evals 评分（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W9 | 1.5 天 | T49 | `main` |

## 目标
有一套固定的 20 个业务问题，每题写好「标准答案要点」和「必须引用的数据行」；一条命令就能跑完，给出每题通过与否和总分；换提示词或换模型时能直接比较好坏。

## 背景
- 实施方案 8 W9 第 1 条、v0.5 指标「AI 问答」。
- `pydantic-evals` 2.66.0（2026-11-04 查，见 prep_notes），不在 `uv.lock`，见 Q1。
- 题目基于 demo 数据（8 个可运行 SKU），因为真实数据尚未核对（W4 遗留）；真实数据题目留到 maken 提供数据后再加。

## 范围
- `tests/eval/questions.yaml`（实施方案 7 节原定位置）：20 题，题型按实施方案：利润排名 5、单 SKU 利润构成 4、异常原因 4、结算总额/费用 4、无答案题 3（应答「数据不足」）。每题字段：`id`、`question`、`expected_facts`（数字以字符串 Decimal 给出，**由代理用确定性代码从 demo 数据算出**并在完成记录里贴计算方法）、`must_cite`（表+ID）、`must_refuse: bool`。
- `src/crosserp/evals/run.py` + `crosserp eval run [--model ...] [--out docs/eval-results/<日期>.json]（实施方案指定的证据目录）`：评分器（全部确定性）：数字全部正确且有引用、必引用行齐全、拒答题确实拒答、无「无来源数字」；可选 LLM-judge 评语气（默认关，⚠ Q2）。
- 离线模式：`--model test` 用 `FunctionModel` 回放 `tests/eval/fixtures/*.json`（录制的工具调用 + 回答），保证 CI 无 key 可跑。
- 结果写 `llm_call.channel="eval"`。
- 提交：`main`，`feat(evals): add 20-question eval set (T50)`；测试不过不提交；不发布。

## 不做
- 不入库评测历史（T51）；不接 CI（T51）。

## 步骤
1. 写评分器单测（全对、错一个数、少引用、该拒没拒）。
2. 写题目与期望（代理生成，标「待 maken 审核」）。
3. 离线回放跑通 20 题；用真实模型由 maken 手工跑。

## 涉及文件
`pyproject.toml` `uv.lock` `tests/eval/{questions.yaml,fixtures/}` `src/crosserp/evals/{__init__,run,scorers}.py` `docs/eval-results/` `src/crosserp/cli.py` `tests/unit/evals/test_scorers.py` `docs/agent.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/evals -q` | passed |
| `uv run crosserp eval run --model test` | 20 题全部完成并输出总分（离线回放应 20/20；这只证明接线正确，指标 5 的 ≥18/20 以真实模型结果为准） |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 打开 `tests/eval/questions.yaml`，逐题看：这是你真的会问的问题吗？标准答案对吗？不对的直接改或写在「问题」里。
- [ ] 配好模型后跑 `uv run crosserp eval run`，结果自动存到 `docs/eval-results/`；指标 5 要求 ≥18/20 且全部带出处。

## 问题
- **Q3 需要 maken 审核 20 道题和标准答案后才能继续。** 这是任务明确的人工审核门槛；代理可以先起草，但不能把未审核题集标为 review。
- **Q1 ⚠ 待 maken 确认：新增依赖 `pydantic-evals`。** 选项：A 加为可选依赖组 `crosserp[eval]`，`src/crosserp/evals` 内延迟导入，普通用户安装不带它（推荐）；B 加为 dev 依赖，评测只能在源码仓库里跑；C 不加，自己写评分循环。
- **Q2 ⚠ 待 maken 确认：是否用另一个模型当「裁判」评回答质量。** 选项：A 不用，只做确定性评分（推荐，可重复、不花钱）；B 可选开启。
- **Q3 ⚠ 待 maken 确认：20 道题由 maken 审核后才算定稿。** 推荐：代理先起草，maken 审核修改后在完成记录里写「已审核」。

## 完成记录
- maken 已审核通过 20 道题和标准答案草稿；题目仍基于合成 demo 数据，真实数据题目留待后续补充。
- 按推荐默认执行 Q1：`pydantic-evals` 放入可选 `eval` 依赖组；Q2 不使用模型裁判，只做确定性评分。
- 完成内容：新增 20 题 YAML、确定性事实/拒答/引用评分器、离线 `--model test` 回放和 `crosserp eval run` 命令。
- 测试结果：评测单元测试 2 passed；`.venv/bin/crosserp eval run --model test` 输出 20/20；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 269 passed、7 skipped，覆盖率 78.32%；ruff/mypy/pre-commit 通过。
