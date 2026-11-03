# T29 业务审计补全：字段齐全 + 与业务修改同一事务 + 全动作覆盖

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W4 | 1.5 天 | T06, T27 | `task/T29-audit-fields` |

## 目标
任意一条业务数据都能查到「谁、什么时候、改前/改后、谁批准的」；写审计失败，业务修改一起回滚。

## 背景
- 实施方案 8 W4 第 4、5 条；安全审计表（第 399 行附近）：`audit_log` 字段 actor_user_id、actor_role、before_json、after_json、approval_id、approver_id、reason、request_id、ip、self_approved，「W1 建表；W4 字段补全」。
- 需要写审计的动作（实施方案原文）：导入、对账、异常处理、映射/费用分类确认、凭证生成、提交审批、批准/驳回、导出、系统配置变更（以及审计导出本身，T31）。其中凭证生成、异常处理、映射确认的功能在 W5/W6 才有，本任务只把**已存在的**动作接上，并提供统一入口让后面的任务直接用。
- 哈希链（T06）：`hash = sha256(prev_hash + 规范化 JSON)`，`audit_head` 行锁（MySQL/PG `SELECT … FOR UPDATE`；SQLite 单写者）。

## 范围
- 迁移 `000x_audit_fields`：`audit_log` 补齐上面 10 个字段中缺的（`actor_user_id String(64) NULL`、`actor_role String(32) NULL`、`approval_id Uuid NULL`、`approver_id String(64) NULL`、`reason String(1000) NULL`、`request_id String(64) NULL`、`ip String(45) NULL`、`self_approved Boolean NOT NULL DEFAULT false`；`before_json`/`after_json` 若 T05 已有则不动）。**新字段全部进入哈希计算**；旧记录的哈希不能变——在 `canonical_json` 里对旧记录缺省字段按「不存在」处理（或升 `hash_version` 字段区分新旧规则），三库测试证明迁移前写的链在迁移后 `audit verify` 仍通过。
- `audit/context.py`：`AuditContext(actor_type, actor_user_id, actor_role, request_id, ip)`；CLI 每次命令生成 `request_id`（uuid4），`actor_user_id` = `--as` 或系统用户名（`getpass.getuser()`），`actor_role` = `"cli"`（W5 接入真实角色）。
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
| `uv run pytest -m db -k audit -q`（三库） | passed，含并发用例（MySQL/PG） |
| 在迁移前的库上写审计 → 升级 → `uv run crosserp audit verify` | 通过 |
| `uv run pytest tests/guard -q` | passed |

## maken 人工验收清单
- [ ] 做一遍 demo + 审批 + 导出，然后 `uv run crosserp audit tail -n 20`：每条都有「谁（你的用户名）」「什么时候」「做了什么」；批准那条有批准人、`self_approved`=是。
- [ ] 用 DB Browser for SQLite 打开 `%USERPROFILE%\.crosserp\data.db`，手工改 `audit_log` 某一行的 reason，保存；运行 `uv run crosserp audit verify` → **必须报错**并指出是哪一条。（改完记得删掉这个库重新 init。）

## 问题

## 完成记录
