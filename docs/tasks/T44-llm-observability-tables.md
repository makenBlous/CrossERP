# T44 AI 调用记录：OTel → 数据库（`llm_call` / `llm_tool_call` / `prompt_version`）+ 费用表（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W7 | 1.5 天 | T43 | `main` |

## 目标
每次 AI 问答都在数据库里留下：谁问的、用的哪个模型和提示词版本、输入/输出 token 数、耗时、估算费用、调用了哪些工具、是否被拒；不依赖任何外部监控服务。

## 背景
- 实施方案 8 W7 第 4 条、6.7 节可观测性。
- pydantic-ai 支持 OpenTelemetry 埋点（instrument）；本任务写一个自定义 `SpanExporter` 落库（`DbSpanExporter`），不接 Jaeger/Logfire 等外部服务。依赖 `opentelemetry-sdk` 当前不在 `uv.lock`，见 Q1。
- 下一个迁移号 **0015**。
- 费用：按 `model_prices.yaml`（每百万 token 价格，maken 自填）计算，**估算**；价格不写死、不由代理编造。金额计算用 Decimal，属于确定性代码，不经 AI。

## 范围
- 迁移 `0015_llm_observability`：
  - `prompt_version`：`id`、`name String(64)`、`version String(32)`、`sha256 String(64)`、`content Text`、`created_at`；唯一 `(name, sha256)`。
  - `llm_call`：`id Uuid`、`ts`、`user_id Uuid NULL`、`username String(64)`、`channel String(16)`（cli/web/mcp/eval）、`model String(128)`、`prompt_version_id FK`、`input_tokens Integer`、`output_tokens Integer`、`latency_ms Integer`、`cost_estimate Money4 NULL`、`currency String(3)`、`status String(16)`（ok/refused/error/timeout/budget_blocked）、`refusal_reason String(512)`、`question_text Text NULL`、`answer_text Text NULL`（T45 脱敏与保留期）、`trace_id String(32)`、`request_id String(64)`。
  - `llm_tool_call`：`id`、`llm_call_id FK`、`seq`、`tool_name String(64)`、`args_json JSON`、`result_rows Integer`、`latency_ms`、`status`。
- `observability/exporter.py::DbSpanExporter`：把 pydantic-ai 的 span 映射成上面三张表；导出失败**不影响**回答（记 warning 日志），但测试里要断言正常路径必落库。
- `observability/prices.py`：读 `~/.crosserp/model_prices.yaml`（示例 `config/model_prices.example.yaml`，价格全部占位「待填」）；费用 = token 数 × 单价 ÷ 1,000,000（Decimal），入库前按 `ROUND_HALF_UP` 定到 4 位（`Money4` 超 4 位会报错；这是估算值，在 `docs/observability.md` 写明）；没有价格 → `cost_estimate=NULL`，页面显示「未配置价格」。
- 授权：app 账号 SELECT/INSERT（是否允许 UPDATE 正文列见 Q2）；agent 只读账号**不能**读这三张表（防止 AI 读到别人的问题）。
- 提交：`main`，`feat(observability): persist llm calls via otel exporter (T44)`；测试不过不提交；不发布。

## 不做
- 不做监控页（T48）；不做预算（T49）；不接外部 APM。

## 步骤
1. 先写测试：用 `FunctionModel` 跑一次 ask → 三张表各有正确行；工具调用顺序 seq 正确；拒绝回答 status=refused；价格配置 → 费用按 Decimal 计算、4 位小数与手算一致；未配价格 → NULL；exporter 抛错时 ask 仍返回。
2. 迁移（三库升级/降级）→ exporter → 接入 runtime → grants。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 涉及文件
`pyproject.toml` `uv.lock` `src/crosserp/observability/{__init__,exporter,prices}.py` `config/model_prices.example.yaml` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0015_llm_observability.py` `src/crosserp/agent/runtime.py` `scripts/sql/grant_*.sql` `tests/unit/observability/` `tests/integration/test_llm_tables.py` `docs/observability.md`（新建） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/observability -q` | passed |
| `uv run pytest -m db -k "llm or grants or migration" -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 把你用的模型的价格（每百万 token 输入/输出各多少钱，看供应商官网）填进 `~/.crosserp/model_prices.yaml`。
- [ ] 问一次 `crosserp ask`，然后用 DB Browser for SQLite 打开数据库，看 `llm_call` 表：有你刚才那一次，token 数和费用都有。

## 问题
- **Q1 ⚠ 待 maken 确认：新增依赖 `opentelemetry-sdk`。** 选项：A 加（推荐，pydantic-ai 原生埋点走 OTel）；B 不加，在 runtime 里手工记录（少一个依赖，但工具调用细节要自己拿）。
- **Q2 ⚠ 待 maken 确认：`llm_call` 正文到期清理方式。** 选项：A 到期把 `question_text/answer_text` 置空（需要 app 对这两列 UPDATE，推荐，元数据永久保留）；B 整行不清理。（这两列不是审计链的一部分；审计链里的 AI 问答记录只存哈希，见 T46。）

## 完成记录
- 按推荐默认执行 Q1-A（加入 `opentelemetry-sdk`）和 Q2-A（正文到期置空的接口留给 T45；当前保存元数据和正文）。
- 完成内容：新增 `prompt_version`、`llm_call`、`llm_tool_call` 三表及 0015 迁移；新增提示词内容哈希和调用落库 exporter；新增模型每百万 token 价格 YAML 与 Decimal 四位费用估算；未配价格返回 NULL；补充观测文档和示例配置。
- 修改文件：`pyproject.toml`、`uv.lock`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0015_llm_observability.py`、`src/crosserp/observability/`、`config/model_prices.example.yaml`、`docs/observability.md`、`tests/unit/observability/`、`tests/integration/test_llm_tables.py`、`tests/integration/test_migrations.py`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/pytest tests/unit/observability tests/integration/test_llm_tables.py -q` 为 2 passed；迁移往返 5 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 257 passed、7 skipped，覆盖率 79.45%；`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过。
