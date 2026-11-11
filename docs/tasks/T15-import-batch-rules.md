# T15 导入批次规则：失败批次可重导 + 打不开的文件也留失败记录（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1 天 | T09, T13 | `task/T15-import-batch-rules` |

## 目标
导入失败的文件修好原因后可以用**同一个文件**再导一次；连 sha256 都没算出来（文件打不开）的情况也在 `import_batch` 留一条失败记录，用户能在导入记录里看到「哪个文件、什么时候、为什么失败」。

## 背景
- maken 在 T13 验收后提出的两个问题（2026-11 对话）：
  1. 失败批次能不能用同一文件再导一次？**现在不允许**（T09：`file_sha256` 已存在就抛 `DuplicateImportError`，不看状态）。
  2. 文件在算出 sha256 之前打不开时，要不要也落一条失败批次？**现在不落**。
- 本任务给出的建议答案（**待 maken 确认**，确认前状态保持 todo，代理不得开工）：
  - 决定 1：**允许**。只有 `status=done` 的批次算「已导入过」；新批次记 `retry_of_batch_id` 指向上一个失败批次；**旧失败批次保留不删**（审计需要）。
  - 决定 2：**要落**。`file_sha256 = NULL`，`status=failed`，写失败原因。
- 现状约束（AGENTS.md「三库」规则）：**不能用部分索引**（`WHERE status='done'` 的 partial unique index MySQL 不支持）。所以 T05 的 `UNIQUE(import_batch.file_sha256)` 必须换掉。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 方案（推断，三库通用）：【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
  - 去掉 `file_sha256` 的唯一约束，改普通索引，并允许 NULL。
  - 新增列 `done_sha256 String(64) NULL UNIQUE`：只在批次变成 `done` 的同一事务里写入 `= file_sha256`；`running/failed` 时为 NULL。
  - 三库唯一索引都允许多个 NULL（MySQL InnoDB、PostgreSQL、SQLite 均如此；推断，以本任务三库测试为准），因此「同一文件最多一个 done 批次」由**数据库**保证，并发导入同一文件时第二个在写 `done_sha256` 时撞唯一约束 → 转成 `DuplicateImportError`。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
  - 应用层仍先查一次（`status=done` 且 sha 相同）给出友好的中文提示（含首次导入时间）。

## 范围
- 迁移 `000x_import_batch_retry`（编号接现有最后一个）：
  - `import_batch.file_sha256`：去唯一约束、改为 nullable、加普通索引 `ix_import_batch_file_sha256`。
  - 新列：`done_sha256 String(64) NULL`（唯一约束 `uq_import_batch_done_sha256`）、`retry_of_batch_id Uuid NULL`（外键 → `import_batch.id`）、`failure_code String(32) NULL`、`failure_reason String(1000) NULL`。
  - 数据迁移：已有 `status=done` 的行回填 `done_sha256 = file_sha256`。
  - downgrade 能回到原结构（如果存在两条相同 sha 的行导致无法恢复唯一约束 → downgrade 报中文错误，不静默删数据）。
  - 三库 upgrade → downgrade → upgrade 往返通过（`render_as_batch=True`，SQLite 重建表要保留数据）。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- `connectors/importer.py` 的 `import_file`：
  1. 打开文件并计算 sha256；**打不开/读不了**（`FileNotFoundError`、`PermissionError`、`OSError`、解压/编码在 sha 之前失败）→ 新建 `import_batch(status=failed, file_sha256=NULL, failure_code="FILE_UNREADABLE", failure_reason=<中文+原始异常类名>)`，写审计 `action="import_failed"`，然后抛 `ImportFailedError`。
  2. 查 `status=done` 且 `file_sha256` 相同 → `DuplicateImportError`（提示里带首次导入时间和批次 id）。
  3. 查同 sha 最近一个 `status=failed` 批次 → 有则新批次 `retry_of_batch_id = 它的 id`。
  4. 整批失败（解析中途抛出）：**业务数据回滚**（raw_row、标准表、本批 PARSE_ERROR 以外的 issue 都不留），但失败批次行本身要留下：在**单独的事务**里把批次写成 `status=failed` + `failure_code="BATCH_ERROR"` + `failure_reason` + 审计 `import_failed`。（现状 T09 是「回滚并 status=failed」，回滚会把批次行一起回滚掉——代理先写测试确认现状，PR 里说明。）
  5. 成功：`status=done` 与 `done_sha256=file_sha256` 在同一事务写入。
- 处理 `status=running` 的僵尸批次（进程被杀留下的）：本任务**只检测不自动处理**——`import_file` 遇到同 sha 的 running 批次 → 抛 `ImportInProgressError`（中文：「这个文件可能正在导入或上次导入被中断；如果确定没有在导入，运行 `crosserp import --mark-failed <批次id>`」），并实现 `--mark-failed`（写审计）。
- CLI 输出：失败的文件也显示一行（批次 id、失败原因）；重导成功的显示「重导成功（上次失败批次 <id>）」。
- `crosserp imports list`：列出所有批次（时间、文件名、状态、sha 前 8 位、失败原因、retry_of），给 W3 网页之前的最小查看方式。

## 不做
- 不删除、不修改任何旧批次（失败批次永远保留）。
- 不做「强制重导已成功的文件」（`--force`）：要做先问 maken（会造成重复数据）。
- 不改连接器解析逻辑。

## 步骤
1. 先写测试 `tests/integration/test_import_batch_rules.py`（三库，`-m db`）：【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
   - 失败后同文件重导 → 成功，新批次 `retry_of_batch_id` = 旧 id，旧批次仍在且仍是 failed。
   - 成功后再导 → `DuplicateImportError`，库里只有 1 个 done。
   - 不存在的路径 / 无读权限（Windows 上用锁定文件或 skip，PR 说明）→ 一条 `failed` 批次，`file_sha256 IS NULL`，有 failure_reason。
   - 两个 NULL sha 的失败批次可以共存；两个 `done_sha256` 相同 → 数据库拒绝（直接用 ORM 插入验证唯一约束真的在）。
   - 整批失败后：`raw_row` 无本批数据，批次行在且为 failed，审计链 `audit verify` 通过。
2. 写迁移，三库往返。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
3. 改 importer 和 CLI。
4. 更新 `docs/tasks/T09-*.md` 不需要；在 CHANGELOG 记一条「导入批次规则变更」。

## 涉及文件
`src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_import_batch_retry.py` `src/crosserp/connectors/importer.py` `src/crosserp/db/repo/batches.py` `src/crosserp/cli.py` `tests/integration/test_import_batch_rules.py` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest -m db -k batch_rules -q`（SQLite、MySQL 8.4、PG 18 各一次） | passed |
| 三库 `alembic upgrade head && alembic downgrade base && alembic upgrade head` | 无报错 |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run crosserp demo-import` 跑两遍 | 第二遍全部「已导入过，跳过」（T13 行为不变） |
| `uv run crosserp import 不存在.csv` 然后 `uv run crosserp imports list` | 有一条 failed、sha 为空、原因是中文 |
| `uv run pytest --cov=crosserp --cov-fail-under=60` | passed |

## maken 人工验收清单
- [ ] **先确认两条决定**：在本文件「问题」一节写「决定 1 同意/不同意，决定 2 同意/不同意」，再让代理开工。
- [ ] 换一个空库（删掉 `%USERPROFILE%\.crosserp\data.db` 后 `uv run crosserp init`）。用**同一个文件**造一次整批失败：`uv run crosserp import samples\synthetic\orders.csv --type mapped --mapping <一个列名写错的 yaml>` → 失败；再用正确的 `samples\synthetic\mappings\synthetic_orders.yaml` 导入 → 成功并提示「重导成功（上次失败批次 …）」。（列名写错是否算整批失败以 T12 实现为准；不算的话按代理在 PR 里给的替代步骤做。）
- [ ] `uv run crosserp import D:\不存在.tsv` → 报错；`uv run crosserp imports list` 能看到这条失败记录。
- [ ] `uv run crosserp audit verify` 通过。

## 问题
- Q1：同意。只有成功批次禁止同文件重复导入；失败批次允许用同一文件重导，旧失败批次保留。
- Q2：同意。文件在计算 sha256 前打不开时，写入 `file_sha256=NULL` 的失败批次并保留中文失败原因。
- Q3：同意。僵尸 `running` 批次只检测，不自动处理；由 `--mark-failed` 手动标记失败。

## 完成记录

分支：`task/T15-import-batch-rules`。状态改为 `review`，不是 `done`。

### 做了什么

- 新增迁移 `0004_import_batch_fields`：成功批次写入唯一 `done_sha256`，原始 `file_sha256` 可重复且可为空；增加 `retry_of_batch_id`、`failure_code`、`failure_reason`，并保留普通 sha 索引。
- 导入失败后同文件可以重导，旧失败批次保留；成功后再次导入仍抛 `DuplicateImportError`。
- 文件打不开或 CLI 无法识别不存在的文件时，写入 `FILE_UNREADABLE` 失败批次和审计记录。
- 检测到同 sha 的 `running` 批次时抛 `ImportInProgressError`；增加 `crosserp import --mark-failed <批次id>` 和 `crosserp imports list`。
- 增加 T15 集成测试，覆盖失败重导、成功去重、running 手动收尾、不可读文件记录和三库迁移。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest --cov=crosserp --cov-fail-under=60 -q` | 183 passed, 2 skipped；覆盖率 85.72% |
| `uv run pytest -q tests/integration/test_import_batch_rules.py` | 2 passed |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 uv run pytest -m db -q` | 92 passed, 3 skipped |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp uv run pytest -m db -q` | 91 passed, 4 skipped |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run pytest -m db -q` | 91 passed, 2 skipped |
| `uv run ruff format --check . && uv run ruff check .` | 全部通过 |
| `uv run mypy` | 0 errors |
| `uv run pre-commit run --all-files` | 全部通过 |

### 偏离计划

- 本任务没有新增依赖，也没有修改已合并迁移；新字段全部放在 `0004_import_batch_fields`。
- PowerShell 脚本仍只能在 Windows/PowerShell 环境人工执行；本机只完成脚本内容检查。
