# T27 审批状态机 `approval/`

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**
> **历史要求说明：** 本卡保留 W4 阶段允许自批的历史实现；现行审批决定和发起人确认均按 08 v4 第 4.6 节及 OpenAPI `critical` 规则执行，不能自批。

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W4 | 1 天 | T26（v0.1 已发布或 maken 同意先开 W4） | `main` |

## 目标
任何要「写出去」的东西先变成一张审批单；批准时锁住内容的哈希，内容一变批准自动失效；所有非法状态跳转直接报错。

## 背景
- 实施方案 8 W4 第 1 条：状态机 draft→pending→approved|rejected；approved→exported；批准时记录 `payload_hash`，内容变化则批准失效（回到 pending）；非法转移抛异常。
- 实施方案 4 节 `approval` 表：id, target_type(voucher_batch/issue_resolution/mapping), target_id, state, requested_by, approver, decided_at, comment, payload_hash。
- 红线（AGENTS.md 第 2 条）：不审批不写账；本任务开始建 `approval/`（AGENTS.md 已在本批次更新允许 W4 起建 approval/ ledger/）。
- W4 还没有用户系统（W5）。`requested_by` / `approver` 先存字符串（CLI `--as <名字>`），W5 接入登录后改为用户 id（推断，PR 说明）。
- W4 还没有凭证（W6）。为了让审批→导出能端到端跑，本周的审批对象用**期间利润报表**：`target_type = "profit_report"`，`target_id = "<store_id>:<period>"`，`payload_hash` = 该报表当前 `inputs_hash`（T20）。（推断：实施方案的 target_type 列表里没有它，属于 W4 演示用的过渡类型，W6 加 `voucher_batch`。）

## 范围
- 迁移 `000x_approval`：`approval(id Uuid, target_type String(32), target_id String(128), state String(16), payload_hash String(64) NULL, requested_by String(64), requested_at, approver String(64) NULL, decided_at NULL, comment String(1000) NULL, token_hash String(64) NULL UNIQUE, used_at NULL, version Integer)`；索引 `(target_type, target_id)`。
- `approval/state.py`：`ApprovalState`（draft/pending/approved/rejected/exported）；转移表：
  - draft → pending（submit）
  - pending → approved（approve，记录 payload_hash、approver、decided_at，生成一次性 `approval_token`：明文只返回给调用方一次，库里只存 sha256）
  - pending → rejected（reject，必须填 comment）
  - approved → exported（只能由 write_service 调用 `mark_exported`）
  - approved → pending（`invalidate`：内容哈希变化时；清空 token）
  - rejected → draft（`reopen`，可选，推断）
  - 其他一律 `IllegalTransition`（中文消息含当前态和目标态）。
- `approval/service.py`：`create`、`submit`、`approve`、`reject`、`reopen`、`check_fresh(approval, current_payload_hash)`（不一致 → 自动 invalidate 并写审计）。乐观锁：`version` 列，更新时 `WHERE version = :v`，0 行受影响 → `ConcurrentModification`。
- 自批：W4 允许同一人提交和批准，但 `audit_log.self_approved = True`（T29 字段）【历史实现，已被 08 v4 第 4.6、12.1 节取代】；是否禁止自批是 W5 角色权限的事（推断）。
- 每个转移都写审计（`action` = `approval.submit/approve/reject/invalidate/reopen`），与状态更新同一事务。
- CLI：`crosserp approval request --target profit_report:<store>:<period> --as <名字>`（创建并提交）、`approval list`、`approval approve <id> --as <名字>`（打印一次性 token）、`approval reject <id> --as <名字> --comment ...`。

## 不做
- 导出（T28）、多级审批（v1.x）、网页审批台（W5）。

## 步骤
1. 先写测试 `tests/unit/approval/test_state.py`：转移表穷举（5×5 每一格都测，合法的成功、非法的抛 `IllegalTransition`）；hypothesis 随机操作序列下状态永远合法；批准后 payload 变 → 回 pending 且旧 token 不能再用。
2. 迁移、service、CLI；三库测试 `-m db -k approval`（含乐观锁冲突）。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 涉及文件
`src/crosserp/approval/{__init__,state,service}.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_approval.py` `src/crosserp/db/repo/approval.py` `src/crosserp/cli.py` `tests/unit/approval/*` `tests/integration/test_approval_db.py` `pyproject.toml`（mypy 覆盖加 approval）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/approval -q` | passed |
| `uv run pytest -m db -k approval -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run crosserp audit verify` | 审批操作后链仍完整 |

## maken 人工验收清单
- [ ] `uv run crosserp demo --no-browser`（或 demo-import + reconcile + profit），然后 `uv run crosserp approval request --target profit_report:<店铺>:2026-10 --as maken`，再 `approval approve <id> --as maken`，记下打印的 token。
- [ ] 再导入一个会改变这个月利润的文件（例如代理给的补充成本表），`uv run crosserp approval list`：这张单应该自动回到「待审批」。
- [ ] `uv run crosserp approval reject <另一张单> --as maken` 不填 `--comment` → 报错要求填写原因。

## 问题

## 完成记录

提交位置：`main`。状态：`review`，没有标记 `done`。

### 做了什么

- 新增 `approval/` 状态机：`draft → pending → approved|rejected`、`approved → exported|pending`、`rejected → draft`，非法转移抛出中文 `IllegalTransition`。
- 新增 `approval` 表和 `0008_approval` 迁移，保存内容哈希、批准人、版本号、一次性 token 哈希和使用时间；乐观锁冲突抛出 `ConcurrentModification`。
- 新增审批服务和 CLI：`approval request/list/approve/reject`；批准只返回一次明文 token，内容哈希变化会自动回到 `pending` 并清空旧 token。
- 每次创建和状态转移与现有业务审计哈希链在同一事务中写入；新增 SQLite、MySQL 8.4、PostgreSQL 18 审批测试。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 按 maken 指示更新 `AGENTS.md` 和任务说明，后续单代理直接在 `main` 开发和提交；T26 保持 `todo`，没有执行发布动作。

### 改动文件

- `src/crosserp/approval/`、`src/crosserp/db/schema.py`、`src/crosserp/db/repo/approval.py`、`src/crosserp/db/migrations/versions/0008_approval.py`
- `src/crosserp/cli.py`
- `tests/unit/approval/`、`tests/integration/test_approval_db.py`、`tests/integration/test_migrations.py`、`tests/guard/test_schema_portable.py`
- `AGENTS.md`、`docs/tasks/README.md`、`CHANGELOG.md`

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest --cov=crosserp --cov-fail-under=60` | `210 passed, 2 skipped`；覆盖率 `85.82%`。跳过项为缺少 Docker 连接串的 MySQL 自检和未提供真实卖家文件。 |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 .venv/bin/python -m pytest -m db -q` | `102 passed, 4 skipped`；MySQL `8.4.13`。 |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp .venv/bin/python -m pytest -m db -q` | `102 passed, 4 skipped`；PostgreSQL `18.6`。 |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `.venv/bin/ruff format --check . && .venv/bin/ruff check .` | `122 files already formatted`，检查通过。 |
| `.venv/bin/mypy --strict` | `Success: no issues found in 75 source files`。 |
| `.venv/bin/pre-commit run --all-files` | `ruff-format`、`ruff`、`mypy` 全部 `Passed`。 |

### 偏离计划

- v0.1.0 没有发布；这是 maken 的明确决定，因此在 T26 保持 `todo` 的情况下先开始 W4。
- 没有新增依赖、没有删除或修改既有迁移、没有创建分支或工作树；新增迁移为 `0008_approval`。
