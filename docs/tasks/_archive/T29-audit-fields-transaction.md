# T29 业务审计补全：字段齐全 + 与业务修改同一事务 + 全动作覆盖

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| doing | W4 | 1.5 天 | T06, T27 | `main` |

## 目标
任意一条业务数据都能查到「谁、什么时候、改前/改后、谁批准的」；写审计失败，业务修改一起回滚。

## 背景
- 实施方案 8 W4 第 4、5 条；安全审计表（第 399 行附近）：`audit_log` 字段 actor_user_id、actor_role、before_json、after_json、approval_id、approver_id、reason、request_id、ip、self_approved，「W1 建表；W4 字段补全」。
- 需要写审计的动作（实施方案原文）：导入、对账、异常处理、映射/费用分类确认、凭证生成、提交审批、批准/驳回、导出、系统配置变更（以及审计导出本身，T31）。其中凭证生成、异常处理、映射确认的功能在 W5/W6 才有，本任务只把**已存在的**动作接上，并提供统一入口让后面的任务直接用。
- 哈希链（T06）：`hash = sha256(prev_hash + 规范化 JSON)`，`audit_head` 行锁（MySQL/PG `SELECT … FOR UPDATE`；SQLite 单写者）。

## 范围
- 迁移 `0010_audit_context`：只新增缺失的 `actor_name String(64) NULL` 和哈希版本标记；已合并的 `actor_user_id UUID`、`approver_id UUID`、`reason String(512)`、`ip String(64)` 均保持不变。`reason` 超过 512 个字符在写入前报错，不截断、不改表。**新字段全部进入哈希计算**；旧记录用旧版本规则验证，三库测试证明迁移前写的链在迁移后 `audit verify` 仍通过。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- `audit/context.py`：`AuditContext(actor_type, actor_user_id, actor_name, actor_role, request_id, ip)`；CLI 没有真实用户时 `actor_user_id` 留空，`actor_name` 记录 `--as` 或系统用户名，W5 接入登录后再填用户 UUID。
- `audit/log.py` 的 `append(...)` 接收 `AuditContext`；新增 `audited(session, ctx, action, target, before, after, **kw)` 上下文管理器：在业务事务内 flush 业务修改后写审计；审计写失败 → 抛出 → 整个事务回滚。
- 接入点（每个都要有测试证明「有审计 + 字段对」）：`import` / `import_failed`（T15）、`recon.run`（T18，after = 汇总数字，不放全部明细）、`profit.snapshot`、`approval.*`（T27）、`ledger.export` / `ledger.export_denied`（T28）、`config.change`（若已有配置写入命令）。
- before/after 规则：JSON 里金额存字符串、时间存 ISO UTC；**不写**密码、token 明文、数据库 URL 里的密码（有测试：审批 token 明文不出现在任何审计行）。
- 并发：`tests/integration/test_audit_concurrency.py`（MySQL/PG）：两个线程各写 50 条 → 链完整、无分叉、`audit verify` 通过。
- 失败回滚：用 monkeypatch 让 `append` 抛错 → 断言业务表没有变化。

## 不做
- 数据库账号权限（T30）、导出/保留（T31）、登录审计 `security_event`（W5）。

## 步骤
1. 先写测试（字段、回滚、并发、旧链兼容、token 不泄露）。
2. 迁移 + context + 各接入点。

## 涉及文件
`src/crosserp/audit/{log,chain,context}.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_audit_fields.py` 各接入点模块（importer、recon/engine、profit/service、approval/service、ledger/write_service、cli） `tests/integration/test_audit_*.py` `tests/unit/test_audit_chain.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest -m db -k audit -q`（三库） | passed，含并发用例（MySQL/PG） |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 在迁移前的库上写审计 → 升级 → `uv run crosserp audit verify` | 通过 |
| `uv run pytest tests/guard -q` | passed |

## maken 人工验收清单
- [ ] 做一遍 demo + 审批 + 导出，然后 `uv run crosserp audit tail -n 20`：每条都有「谁（你的用户名）」「什么时候」「做了什么」；批准那条有批准人、`self_approved`=是。
- [ ] 用 DB Browser for SQLite 打开 `%USERPROFILE%\.crosserp\data.db`，手工改 `audit_log` 某一行的 reason，保存；运行 `uv run crosserp audit verify` → **必须报错**并指出是哪一条。（改完记得删掉这个库重新 init。）

## 问题

maken 已确认 T29 的字段口径：

- `actor_user_id`、`approver_id` 保持现有 `Uuid NULL`。
- `reason` 保持现有 `String(512)`，超过 512 个字符时写入前报错，不截断。
- `ip` 保持现有 `String(64)`。
- CLI 没有真实用户时 `actor_user_id` 留空，新增 `actor_name String(64) NULL` 保存 `--as` 或系统用户名；W5 再填用户 UUID。
- 迁移只新增缺失字段，不改不删已有列；新字段进入哈希计算，旧记录哈希必须继续通过验证。

已获得继续实现授权，状态恢复为 `doing`。

## 完成记录

提交位置：`main`。状态：`review`，没有标记 `done`。

### maken 决定与实现口径

- 不修改已合并字段：`actor_user_id`、`approver_id` 保持 UUID，`reason` 保持 512 字符，`ip` 保持 64 字符。
- 新增 `actor_name String(64) NULL`：CLI 没有真实用户时 `actor_user_id` 留空，`--as` 或系统用户名写入 `actor_name`。
- 新增 `hash_version`：旧记录按版本 1 的哈希字段验证，新记录按版本 2 把 `actor_name` 和版本号纳入哈希；迁移不改写旧哈希。
- `reason` 超过 512 字符在 `append` 写入前报错，不截断、不修改表结构。

### 做了什么

- 新增 `0010_audit_context` 迁移和 `AuditContext` / `audited(...)` 事务辅助器。
- 审计哈希链支持新旧版本；新增 actor_name 字段，`audit tail` 优先显示操作者名称。
- 对账运行写入 `recon.run` 摘要审计，利润快照写入 `profit.snapshot` 摘要审计；审批和导出沿用 T27/T28 审计并带操作者名称。
- 新增旧哈希兼容、超长 reason、actor_name、审计失败回滚和三库迁移/审计测试。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

### 改动文件

- `src/crosserp/audit/{log.py,context.py,__init__.py}`
- `src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0010_audit_context.py`
- `src/crosserp/recon/engine.py`、`src/crosserp/profit/service.py`、`src/crosserp/approval/service.py`、`src/crosserp/cli.py`
- `tests/unit/test_audit_hash.py`、`tests/integration/test_audit_chain.py`、`tests/property/test_audit_tamper.py`
- `docs/tasks/README.md`、`CHANGELOG.md`

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest --cov=crosserp --cov-fail-under=60` | `218 passed, 2 skipped, 1 xfailed`；覆盖率 `85.77%`。 |
| `.venv/bin/python -m pytest -m db -k audit -q` | SQLite `15 passed`。 |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 .venv/bin/python -m pytest -m db -k audit -q` | MySQL 8.4 `15 passed`。 |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp .venv/bin/python -m pytest -m db -k audit -q` | PostgreSQL 18 `15 passed`。 |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 .venv/bin/python -m pytest -m db -q` | MySQL 8.4 `108 passed, 4 skipped`。 |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp .venv/bin/python -m pytest -m db -q` | PostgreSQL 18 `108 passed, 4 skipped`。 |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `.venv/bin/ruff format --check . && .venv/bin/ruff check .` | 通过。 |
| `.venv/bin/mypy --strict` | 通过。 |

### 偏离计划

- 按 maken 决定，没有改动任何已合并列的类型或长度；只新增 `actor_name` 和 `hash_version`。
- 没有新增依赖、没有创建分支或工作树；直接在 `main` 开发和提交。
