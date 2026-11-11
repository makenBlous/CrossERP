# T28 唯一写出口 `ledger/write_service.py` + 守卫测试（指标 4）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W4 | 1.5 天 | T27 | `main` |

## 目标
系统里只有一个函数能把东西「写出去」，它没看到有效审批就拒绝并留审计；测试从三个方向保证没人能绕过去。

## 背景
- 实施方案 8 W4 第 2、3 条；4 节 `export_artifact`（id, approval_id, target_id(kingdee/xlsx/erpnext), file_path/ext_ref, sha256, created_at）；2.3 `LedgerTarget.push(batch, approval)`；指标 4「不审批不写账」（证据：tests/guard + audit verify + 权限矩阵测试）。
- W4 的导出目标只有 `xlsx`（把 T27 已批准的期间利润报表写成文件，复用 T22）；金蝶/ERPNext 目标是 W6 以后（推断：用 xlsx 让审批→导出在 W4 就能端到端验证）。

## 范围
- 迁移 `000x_export_artifact`：`export_artifact(id, approval_id FK, target_id String(32), file_path String(1000) NULL, ext_ref String(255) NULL, sha256 String(64), created_at)`。
- `ledger/targets/base.py`（`LedgerTarget` 协议，T09 已有类型定义则移过来）、`ledger/targets/xlsx.py`（写到 `exports/` 目录，文件名含 approval id，已存在不覆盖）。
- `ledger/write_service.py`：`export(session, batch_id, target_id, approval_token) -> ExportArtifact`，按顺序检查：
  1. 有 `token_hash = sha256(approval_token)` 的审批单，且其 `target_id` 对应 `batch_id`；
  2. `state == approved`；
  3. 当前 payload_hash（重新计算）== 批准时的 `payload_hash`；
  4. `used_at IS NULL`（未被使用）。
  任一失败 → 抛 `ApprovalRequired(reason_code)`（中文消息），并在**独立事务**写审计 `action="ledger.export_denied"`（`reason` = 哪一条没过）——拒绝记录不能因为外层回滚而丢失。
  成功 → 调 target 生成产物 → 同一事务内：写 `export_artifact`、`approval` 改 exported + `used_at`、审计 `ledger.export`。产物写文件失败 → 事务回滚，审批仍是 approved。
- CLI：`crosserp export --target xlsx --batch profit_report:<store>:<period> --token <token>`；不给 token 也允许调用（用于验证会被拒绝）。另加只读的 `crosserp audit tail [-n 20]`（按时间倒序打印最近审计：时间 Asia/Shanghai、actor、action、target、reason）。
- `tests/guard/`：
  - `test_denials.py`：无审批、已驳回、内容被改、重复使用 4 种情况都抛 `ApprovalRequired`，且每次都多一条 `export_denied` 审计、没有新产物文件。
  - `test_import_boundary.py`：AST 扫描 `src/crosserp/**.py`，除 `ledger/write_service.py` 和 `ledger/targets/` 自身外，任何模块 `import`/`from` `crosserp.ledger.targets` → 失败（含 `importlib.import_module("crosserp.ledger.targets...")` 字符串的情况）。
  - `test_agent_session_readonly.py`：见 T30（只读会话）；T30 未完成时此文件标记 `xfail(strict=True)` 并写明原因。
- 守卫测试在 CI 必跑（`-m guard` 不得被默认跳过）。

## 不做
- 金蝶/ERPNext 目标、凭证（W6+）。
- 不在 write_service 以外的地方写任何外部文件/系统。

## 步骤
1. 先写 `tests/guard/` 全部测试（此时应失败），再实现。
2. 三库跑 `-m db -k "guard or export"`。

## 涉及文件
`src/crosserp/ledger/{__init__,write_service}.py` `src/crosserp/ledger/targets/{__init__,base,xlsx}.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_export_artifact.py` `src/crosserp/cli.py` `tests/guard/*` `.github/workflows/ci.yml` `pyproject.toml`（mypy 加 ledger）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/guard -q` | passed（T30 前 readonly 用例为 xfail） |
| `uv run crosserp export --target xlsx --batch profit_report:<store>:2026-10` | 拒绝，退出码非 0，中文说明「没有有效审批」 |
| 用 T27 的 token 导出两次 | 第一次成功生成文件，第二次拒绝「审批已被使用」 |
| `uv run crosserp audit verify` | 通过 |

## maken 人工验收清单
- [ ] **不审批直接导出**：`uv run crosserp export --target xlsx --batch profit_report:<店铺>:2026-10` → 必须被拒绝。
- [ ] 按 T27 走一遍申请 + 批准，用 token 导出 → `exports\` 下出现文件；同一个 token 再导一次 → 被拒绝。
- [ ] `uv run crosserp audit tail -n 10`，能看到「拒绝」（export_denied）和「导出」（export）两类记录，拒绝记录写了原因。

## 问题

## 完成记录

提交位置：`main`。状态：`review`，没有标记 `done`。

### 做了什么

- 新增 `ledger/write_service.py` 作为唯一写出入口，支持 `xlsx` 目标；没有有效审批、对象不一致、审批未批准、内容哈希变化或 token 已使用时拒绝。
- 新增 `export_artifact` 表和 `0009_export_artifact` 迁移，成功导出记录文件路径、SHA-256、审批单和创建时间；文件已存在时不覆盖。
- 新增 `ledger/targets/base.py`、`ledger/targets/xlsx.py`，并用 AST 守卫确保其他模块不能绕过 `write_service` 导入写出目标。
- 拒绝动作通过独立会话写 `ledger.export_denied` 审计；成功动作写 `ledger.export`，审批 token 只允许使用一次。
- 新增 `crosserp export` 和 `crosserp audit tail` CLI；T30 前的智能体只读会话测试保留为严格 xfail。
- 修正 `0009_export_artifact` 回滚顺序，先删外键再删索引，兼容 MySQL 8.4。

### 改动文件

- `src/crosserp/ledger/`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0009_export_artifact.py`、`src/crosserp/cli.py`
- `tests/guard/`、`tests/integration/test_migrations.py`
- `docs/tasks/README.md`、`CHANGELOG.md`

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/guard -q` | `13 passed, 1 xfailed`；xfailed 是 T30 只读会话占位。 |
| `.venv/bin/python -m pytest --cov=crosserp --cov-fail-under=60` | `214 passed, 2 skipped, 1 xfailed`；覆盖率 `85.66%`。 |
| `.venv/bin/python -m pytest -m db -q` | SQLite `105 passed, 4 skipped`。 |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 .venv/bin/python -m pytest -m db -q` | MySQL 8.4 `106 passed, 3 skipped`。 |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp .venv/bin/python -m pytest -m db -q` | PostgreSQL 18 `105 passed, 4 skipped`。 |
| `.venv/bin/ruff format --check . && .venv/bin/ruff check .` | `131 files already formatted`，检查通过。 |
| `.venv/bin/mypy --strict` | `Success: no issues found in 81 source files`。 |
| `.venv/bin/pre-commit run --all-files` | `ruff-format`、`ruff`、`mypy` 全部 `Passed`。 |

### 偏离计划

- 没有新增依赖、没有修改既有迁移；新增迁移为 `0009_export_artifact`。
- 按 maken 的单代理要求直接在 `main` 修改和提交，没有创建分支或工作树。
