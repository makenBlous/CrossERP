# T30 数据库账号权限（MySQL/PG）+ 智能体只读会话

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W4 | 1 天 | T16, T29 | `task/T30-db-grants` |

## 目标
就算代码有 bug，数据库本身也不让应用改审计记录、不让智能体写任何表。

## 背景
- 实施方案 8 W4 第 3c、6 条：`scripts/sql/grant_mysql.sql`、`grant_pg.sql` + `docs/db-grants.md`——应用账号对 `audit_log`、`security_event` 只有 INSERT/SELECT；智能体账号对全部表只有 SELECT。W4 验收：在 MySQL/PG 上用应用账号执行 `UPDATE audit_log` 被数据库拒绝。
- `security_event` 表 W5 才建；脚本里先写好（表不存在时跳过或注释说明，推断）。
- `audit_head` 需要 UPDATE（链头推进），这是应用账号对审计相关表**唯一**的 UPDATE 权限；`audit_checkpoint`、`audit_export` 只 INSERT/SELECT（T31）。
- SQLite 没有账号权限：只读会话用 `file:...?mode=ro` URI 打开（Python `sqlite3` 官方支持 URI 模式），**不提供** SQLite 上的「审计不可改」保证——文档写明「生产请用 MySQL/PG」。

## 范围
- 三个账号（名字可在脚本顶部变量改）：`crosserp_owner`（迁移用，DDL）、`crosserp_app`（应用）、`crosserp_agent`（智能体，只读）。密码**不写进脚本**：脚本用占位符，`docs/db-grants.md` 说明怎么替换。
- `grant_mysql.sql`（MySQL 8.4）与 `grant_pg.sql`（PG 18）：app 对业务表 SELECT/INSERT/UPDATE/DELETE；对 `audit_log`、`security_event`、`audit_checkpoint`、`audit_export` 只 SELECT/INSERT；`audit_head` SELECT/UPDATE；agent 全部表只 SELECT；PG 用 `ALTER DEFAULT PRIVILEGES` 让以后新建的表也遵守（MySQL 没有等价物：文档写明「每次加表的迁移后重跑授权脚本」，CI 会检查）。
- 配置：`CROSSERP_DATABASE_URL`（app）、`CROSSERP_MIGRATE_DATABASE_URL`（owner，`init`/迁移用，没设则用前者）、`CROSSERP_AGENT_DATABASE_URL`（agent）。
- `db/session.py`：`readonly_session()`：MySQL/PG 用 agent URL，并额外 `SET SESSION TRANSACTION READ ONLY`（MySQL）/ `SET default_transaction_read_only = on`（PG）双保险；SQLite 用 `mode=ro`。方言差异放 `db/dialects.py`。
- CI db-matrix（MySQL/PG 格）：建三个账号 → 跑授权脚本 → 用 app 账号跑测试；`tests/integration/test_grants.py`：app 账号 `UPDATE audit_log` / `DELETE FROM audit_log` → 数据库报权限错误；agent 账号对任一业务表 INSERT → 报错；app 正常导入/对账/审批/导出全部成功。
- T28 的 `test_agent_session_readonly.py` 去掉 xfail，三库都要拒绝写入。

## 不做
- 不在任何地方保存真实密码；不做账号自动创建命令（文档 + SQL 脚本即可）。

## 步骤
1. 先写 `test_grants.py` 和只读会话测试。
2. 写两个 SQL 脚本、文档、CI 步骤；在 CI 里跑通。

## 涉及文件
`scripts/sql/grant_mysql.sql` `scripts/sql/grant_pg.sql` `docs/db-grants.md` `src/crosserp/db/session.py` `src/crosserp/db/dialects.py` `src/crosserp/config.py` `.github/workflows/ci.yml` `tests/integration/test_grants.py` `tests/guard/test_agent_session_readonly.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 / 检查 | 期望 |
|---|---|
| CI db-matrix mysql / postgres 格 | 授权脚本执行成功，`test_grants` passed |
| `uv run pytest tests/guard -q` | passed，无 xfail |
| CI 日志 | app 账号 `UPDATE audit_log` 的报错原文可见（MySQL `ER_TABLEACCESS_DENIED_ERROR`/PG `permission denied`，以实际输出为准） |

## maken 人工验收清单
- [ ] 打开 PR 的 CI 日志，找到「UPDATE audit_log 被拒绝」那一步，截图。
- [ ] （有 Docker 时）按 `docs/db-grants.md` 在本机 MySQL 上执行脚本，用 app 账号登录 `mysql` 客户端执行 `UPDATE audit_log SET reason='x';` → 应报权限错误。

## 问题

## 完成记录
