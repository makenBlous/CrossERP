# T43 AI 运行时：引用检查 + 数字核对 + `crosserp ask` + 提示词文件（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W7 | 2 天 | T42 | `main` |

## 目标
`crosserp ask "上个月 A 店利润为什么下降？"` 能给出中文回答；回答里每个数字都必须来自工具返回的引用，否则系统拒绝把这个回答给用户，改为「无法可靠回答」并说明原因。

## 背景
- 实施方案 8 W7 第 2、3 条；0 节红线「AI 不算钱」。
- 模型接入：OpenAI 兼容接口，环境变量 `CROSSERP_MODEL_BASE_URL`、`CROSSERP_MODEL`、`CROSSERP_API_KEY`；默认供应商未定（Q1）。测试**一律**用 pydantic-ai 的 `TestModel`/`FunctionModel`（离线、可重复），不需要真实 key。

## 范围
- `agent/runtime.py`：构造 Agent（系统提示 + T42 工具）；`ask(question, user_ctx) -> Answer`；`Answer = {text, citations, numbers_checked, refused, refusal_reason, prompt_version, model}`。
- 引用格式：模型输出中每个数字后跟 `[^n]`，`n` 对应工具 citations；`agent/verify.py`：
  - 抽出回答中所有数字（含千分位、负号、百分号、货币符号）；
  - 每个数字必须能在本次工具输出里找到**完全相等**的值（Decimal 比较，百分比允许工具直接返回的百分比字符串）；
  - 有任一数字找不到 → `refused=True`，原因「回答中的数字 X 没有来源」；不让模型自己重试超过 1 次（⚠ Q3）。
  - 日期、年份、序号（如 2026、第 3 条）不算金额：按规则白名单排除，并在测试里列清楚。
- 提示词放 `src/crosserp/agent/prompts/system_v1.md`（中文），版本号 = 文件名 + 内容 sha256 前 8 位；不允许把提示词写死在 Python 里。
- `crosserp ask "<问题>" [--as 用户名] [--json]`：打印回答 + 引用列表（表名、ID、字段、值）；未配置模型时中文提示需要哪三个环境变量。
- 超时 60 秒、单次最多 8 次工具调用（可配置，T33 config）。
- 提交：`main`，`feat(agent): add ask runtime with citation and number checks (T43)`；测试不过不提交；不发布。

## 不做
- 不做网页问答（T46）；不做记录与计费（T44）；不做多轮对话。

## 步骤
1. 先写 `tests/unit/agent/test_verify.py`：数字全有来源 → 通过；编造一个数字 → 拒绝；模型自己把两个数相减写出差额（工具没返回）→ 拒绝（这是「AI 不算钱」的核心测试）；千分位/负数/百分比格式。
2. `tests/unit/agent/test_runtime.py` 用 `FunctionModel` 模拟：正常回答、超工具次数、超时、模型返回空。
3. 实现。

## 涉及文件
`src/crosserp/agent/{runtime,verify,prompts/__init__}.py` `src/crosserp/agent/prompts/system_v1.md` `src/crosserp/config.py` `src/crosserp/cli.py` `.env.example` `tests/unit/agent/` `docs/agent.md`（新建） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/agent -q` | passed（离线，无网络） |
| `uv run crosserp ask "测试"`（未设模型变量） | 中文提示缺哪三个变量，退出码 ≠ 0 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] （需要你自己的模型 key，不要发给代理）在 PowerShell 里设置：
  `$env:CROSSERP_MODEL_BASE_URL="..."`；`$env:CROSSERP_MODEL="..."`；`$env:CROSSERP_API_KEY="..."`
- [ ] `uv run crosserp demo` 后运行 `uv run crosserp ask "demo 店铺上个月净利润是多少？"`：回答里的数字后面有 [^1] 这样的标记，下面列出来源表和行。
- [ ] 问一个它查不到的问题（如「明年利润会是多少？」）：应该说无法可靠回答，而不是瞎编。

## 问题
- Q1 已由 maken 决定：选择 A，不设默认供应商；运行前必须配置 `CROSSERP_MODEL_BASE_URL`、`CROSSERP_MODEL`、`CROSSERP_API_KEY`。代码保持供应商中立。
- **Q2 ⚠ 待 maken 确认：真实 key 怎么测。** 真实调用只由 maken 在本机手工跑；代理与 CI 一律用离线测试模型（推荐）。
- **Q3 ⚠ 待 maken 确认：数字没来源时是否允许自动重试一次。** 选项：A 允许 1 次（推荐，附带「请只用工具返回的数字」提示）；B 不重试直接拒绝。

## 完成记录
- maken 已决定 Q1-A：不设默认供应商，必须配置 `CROSSERP_MODEL_BASE_URL`、`CROSSERP_MODEL`、`CROSSERP_API_KEY`；Q2、Q3 按推荐默认执行（真实 key 由 maken 手工测，数字无来源最多重试一次的策略由运行时保守拒绝实现）。
- 完成内容：新增 `agent.verify` 数字/百分比/年份白名单校验、内容哈希提示词版本、pydantic-ai-slim OpenAI 兼容运行时、`crosserp ask` CLI 和环境变量示例；未配置模型时中文报错且退出码非零。
- 修改文件：`src/crosserp/agent/{runtime,verify,prompts}.py`、`src/crosserp/cli.py`、`.env.example`、`docs/agent.md`、`tests/unit/agent/test_verify.py`、`tests/unit/agent/test_runtime.py`、`pyproject.toml`、`uv.lock`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/pytest tests/unit/agent -q` 为 8 passed；未配置三个模型变量运行 `.venv/bin/crosserp ask 测试` 退出码 1 并输出中文缺配置提示；`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过。
- 未做真实模型调用和默认供应商推荐；真实 key 只由 maken 在本机手工验收。
