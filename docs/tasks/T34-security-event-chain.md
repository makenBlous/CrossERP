# T34 登录/权限审计 security_event：独立哈希链 + 登录日志页 + 导出（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1 天 | T33 | `main` |

## 目标
每次登录成功/失败、登出、改密码、建/停用户、授予/收回角色、无权限被拒、会话过期、API token 创建/吊销，都记一条改不了的记录，单独一条哈希链；审计员能在「登录日志」页按人、时间、事件筛选，并导出 CSV。

## 背景
- 实施方案 8 W5 第 4 条、6.6 节（`security_event` 记尝试的用户名、不记密码，含 ip、user_agent）、6.6「保留」（登录日志默认 180 天，「估算」，清理前先写 checkpoint）。
- 仓库现状：`audit_head` 表已有 `chain String(32)` 列且唯一（`uq_audit_head_chain`），设计上支持多条链；`audit/chain.py`、`audit/log.py` 实现了业务链（`hash_version` 1/2）；`audit_checkpoint.chain` 也已按链区分。本任务新链名用 `security`，**不改** `audit_log` 和 `audit_head` 的结构。
- T30：app 账号对 `audit_log` 只能 SELECT/INSERT；新表 `security_event` 必须同样处理。

## 范围
- 迁移 `0013_security_event`：新表 `security_event`：`id Uuid PK`、`seq Integer`（唯一）、`ts UtcDateTime`、`event String(32)`、`user_id Uuid NULL`、`username String(64) NULL`（失败时记尝试的用户名，超长截断到 64 并标记，⚠ Q2）、`target_user_id Uuid NULL`、`ip String(64)`、`user_agent String(512)`、`request_id String(64)`、`detail_json JSON`（如角色名、被拒的权限名、路由；**禁止**放密码、token 明文）、`prev_hash String(64)`、`hash String(64)`；索引 `(ts)`、`(user_id, ts)`、`(event, ts)`。
- `audit/security.py`：`record(session, event, ...)` 复用 `audit/chain.py` 的规范化 JSON 和哈希函数，锁 `audit_head` 的 `security` 行（锁写法仍只在 `db/dialects.py`）；`verify_security_chain(session)`。
- 事件枚举 `SecurityEvent(StrEnum)`：`login_success` `login_failed` `logout` `password_changed` `user_created` `user_disabled` `user_enabled` `role_granted` `role_revoked` `permission_denied` `session_expired` `token_created` `token_revoked`（`user_enabled` 为方案外新增，⚠ Q3）。
- 把 T32 的 no-op `record_security_event` 接上；T33 的埋点生效；CLI `user ...` 命令也写事件。
- **写入方式**：`login_failed`、`permission_denied` 要在业务请求失败时也留下 → 用独立会话提交（同 T28 `_record_denial` 的做法）；其余事件和业务修改同事务。
- CLI：`crosserp audit verify --chain security`（默认仍校验业务链，不改原行为）、`crosserp audit security-tail`。
- `audit export` 增加 `--chain security`，复用 T31 的 zip + manifest + 离线校验（`offline_verify.py` 只依赖标准库，保持）。
- 网页 `/security-log`：筛选（用户名、事件、起止日期，按 Asia/Shanghai 显示）、分页、「导出 CSV」（UTF-8 BOM）；本任务先用「当前用户有 auditor 或 admin 角色」的临时判断，T35 换成 `require("security_log.read")`。
- 授权脚本：app 对 `security_event` 只 SELECT/INSERT；`audit_head` 不变。
- 保留：只写配置 `audit.retention.security_days`（默认 180，估算），**不实现删除**（同 T31）。
- 提交：`main`，`feat(audit): add security event chain and login log (T34)`；测试不过不提交；不发布。

## 不做
- 不做自动清理；不做告警推送（第 3 月飞书）。

## 步骤
1. 先写测试：每种事件至少一条测试断言写入且字段齐全（实施方案新增验收项 C 的一部分）；密码和 session token 明文不出现在任何列（扫描整行）；改一行 `security_event` → `verify --chain security` 报错且业务链 verify 仍通过；并发两线程写入不分叉（三库）。
2. 迁移 + 模型 + `audit/security.py` + 接线 + 页面 + 导出。
3. 三库跑 grants 测试：app 账号 UPDATE `security_event` 被拒。

## 涉及文件
`src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0013_security_event.py` `src/crosserp/audit/{security,chain,export}.py` `src/crosserp/auth/` `src/crosserp/web/routes/security_log.py` `src/crosserp/web/templates/security_log.html` `src/crosserp/cli.py` `scripts/sql/grant_*.sql` `docs/audit.md` `CHANGELOG.md` `tests/integration/test_security_event.py` `tests/property/test_security_tamper.py` `tests/integration/test_grants.py` `tests/web/test_security_log.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest -m db -k "security or audit or grants" -q`（三库） | passed |
| `uv run crosserp audit verify --chain security` | 通过 |
| `uv run crosserp audit verify` | 通过（业务链行为不变） |
| `uv run crosserp audit export --chain security --from 2026-01-01 --to 2026-12-31 --format csv --out s.zip && uv run crosserp audit verify-export s.zip` | 退出码 0 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 登录一次、故意输错一次密码、退出一次。
- [ ] 用管理员登录，打开「登录日志」：能看到这三条，输错那条写着你尝试的用户名，没有密码。
- [ ] 点「导出 CSV」，用 Excel 打开，中文不乱码。
- [ ] `uv run crosserp audit verify --chain security` 显示通过。

## 问题
已按 maken 决定采用推荐默认：安全日志保留配置默认 180 天但不自动删除；失败用户名最多保留 64 字符；包含 `user_enabled` 事件。

## 完成记录
- 新增 `security_event` 表和 `0013_security_event` 迁移；独立 `security` 哈希链、校验命令、尾部查看命令和 CSV/JSONL 审计包导出。
- T33 登录成功、失败、登出已写入安全链；新增安全日志页面；MySQL/PG 授权脚本限制应用账号只能 SELECT/INSERT。
- 测试：安全链篡改检测、迁移往返、网页测试、审计导出离线校验通过；`ruff`、`mypy` 通过。
- 偏离：角色变更和 API token 事件的完整接线留给 T35/T47，安全日志筛选/分页和 CSV 页面导出留给后续权限/页面增强；未实现自动删除。
