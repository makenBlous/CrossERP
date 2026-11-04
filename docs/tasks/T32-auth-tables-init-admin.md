# T32 用户 / 角色 / 会话表 + argon2 + `init` 建第一个管理员（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W5 | 1.5 天 | T31（maken 同意开 W5） | `main` |

## 目标
数据库里有「用户、角色、登录会话、API token、系统设置」五张新表；`crosserp init` 能建出第一个管理员（拥有全部 5 个角色、默认打开单人模式）；还有 `crosserp user ...` 命令行能在没有网页时管理用户。

## 背景
- 实施方案 8 W5 第 1 条（init 建首个管理员、argon2）、2.4 节（5 个角色；init 账号拥有全部角色且单人模式打开）、4 节（`app_user`、`user_role`、`session`、`api_token` 字段）。
- 仓库现状（HEAD `57190c2`）：`src/crosserp/` 下**没有** `auth/` 目录，也没有任何用户表；最新迁移是 `0011_audit_export`，本任务新迁移为 `0012_auth`。`audit_log.actor_user_id` / `approver_id` 已是 `Uuid NULL`（T29），本任务不改它们。
- `crosserp init`（`cli.py`）现在只做「建库目录 → 迁移 → 自检」，重复执行无副作用；这一特性必须保留。
- argon2-cffi 最新 25.1.0（https://pypi.org/project/argon2-cffi/ ，2026-11-04 实查）；AGENTS.md 第 2 节写了「v0.5+ 才装 argon2-cffi 25.1」，加依赖仍要 maken 点头（见「问题」Q1）。
- T30 完成记录：MySQL 授权脚本是**逐表**授权，新增表后必须更新 `scripts/sql/grant_mysql.sql` / `grant_pg.sql` 并重跑。

## 范围
- 新目录 `src/crosserp/auth/`（AGENTS.md 第 3 节目前写着「不要建」，合并 AGENTS 补丁后放开）：
  - `auth/passwords.py`：`hash_password(plain) -> str`、`verify_password(hash, plain) -> bool`、`needs_rehash(hash)`，用 `argon2.PasswordHasher` 默认参数；密码最短 10 位（⚠ Q3），不做复杂度规则。
  - `auth/roles.py`：`Role(StrEnum)` = `admin` `finance` `operator` `viewer` `auditor`。
  - `db/repo/users.py`：`create_user`、`get_by_username`、`grant_role`、`revoke_role`、`set_active`、`set_password`、`list_users`（数据库读写只在 repo）。
- 迁移 `0012_auth`（只新增表，不碰已有表）：
  - `app_user`：`id Uuid PK`、`username String(64) UNIQUE`、`display_name String(128)`、`password_hash String(255)`、`is_active Boolean`、`failed_logins Integer default 0`、`locked_until UtcDateTime NULL`、`password_changed_at UtcDateTime`、`must_change_password Boolean default false`（T36 重置密码用）、`created_at UtcDateTime`。
  - `user_role`：`user_id → app_user.id`、`role String(16)`、`granted_by Uuid NULL`、`granted_at`；唯一约束 `(user_id, role)`。
  - `user_session`（⚠ Q2 表名）：`id String(64) PK`（存 token 的 sha256，cookie 里放明文）、`user_id`、`created_at`、`expires_at`、`last_seen_at`、`ip String(64)`、`user_agent String(512)`、`csrf_token_hash String(64)`、`revoked_at NULL`。
  - `api_token`：`id`、`user_id`、`name String(64)`、`token_hash String(64) UNIQUE`、`scopes JSON`、`created_at`、`last_used_at NULL`、`revoked_at NULL`（本任务只建表，T47 才用）。
  - `app_setting`（⚠ Q4）：`key String(64) PK`、`value_json JSON`、`updated_by Uuid NULL`、`updated_at`；单人模式存为 `solo_mode = true/false`。
- `crosserp init` 增加：库里没有任何 `app_user` 时，交互提示输入管理员用户名和两次密码（`--admin-username`、`--admin-password-stdin` 供脚本用）；建用户 + 授 5 个角色 + `solo_mode=true`，同一事务写业务审计 `user.create`（`actor_type=system`，`actor_name` = 系统用户名，`actor_user_id` NULL，按 T29 规则）。已有用户时**什么都不问**，保持幂等。
- `crosserp user add|list|grant|revoke|disable|enable|passwd`（`--as <用户名>` 记操作者；CLI 下 `actor_user_id` 填该用户 UUID，找不到用户则报错）。security_event 由 T34 接入，本任务先在 `auth/` 留一个 `record_security_event(...)` 空实现（no-op + TODO T34）。
- 更新 `scripts/sql/grant_mysql.sql`、`grant_pg.sql`：app 对 5 张新表 SELECT/INSERT/UPDATE（不给 DELETE，⚠ Q5），agent 账号**不给** `app_user`、`user_session`、`api_token` 的 SELECT（防止 AI 读到密码哈希）。
- `demo` 命令：演示库里自动建 `demo` / 随机密码并打印一次（⚠ Q6）。
- `docs/database.md` 增加新表说明；`CHANGELOG.md`。
- 提交：直接在 `main`，信息形如 `feat(auth): add user tables and init admin (T32)`；任何测试不过不提交；不打 tag、不推送发布。

## 不做
- 不做网页登录、cookie、CSRF（T33）；不写 security_event（T34）；不做权限检查（T35）；不做 SSO/LDAP/找回密码邮件。
- 不改任何已有表、不改已合并迁移。

## 步骤
1. 先写测试：`tests/unit/auth/test_passwords.py`（哈希不等于明文、错误密码失败、同一密码两次哈希不同）；`tests/integration/test_auth_tables.py`（三库建表、唯一约束、中文 display_name、emoji）；`tests/integration/test_init_admin.py`（空库 init 建管理员 + 5 角色 + solo_mode；再跑 init 不再提问；审计链 verify 通过）。
2. 写迁移与 `schema.py` 模型；`tests/integration/test_migrations.py` 往返测试自动覆盖新表（确认确实覆盖）。
3. 写 `auth/`、`db/repo/users.py`、CLI。
4. 更新授权脚本，三库跑 `tests/integration/test_grants.py`，补一条「agent 账号读 app_user 被拒」的测试。

## 涉及文件
`pyproject.toml` `uv.lock`（加 argon2-cffi） `src/crosserp/auth/{__init__,passwords,roles}.py` `src/crosserp/db/schema.py` `src/crosserp/db/repo/users.py` `src/crosserp/db/migrations/versions/0012_auth.py` `src/crosserp/cli.py` `src/crosserp/demo/__init__.py` `scripts/sql/grant_mysql.sql` `scripts/sql/grant_pg.sql` `docs/database.md` `docs/db-grants.md` `CHANGELOG.md` `tests/unit/auth/` `tests/integration/test_auth_tables.py` `tests/integration/test_init_admin.py` `tests/integration/test_grants.py` `tests/guard/test_schema_portable.py`（仅当守卫需要登记新表时追加，不删条目）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/auth tests/integration/test_auth_tables.py tests/integration/test_init_admin.py -q` | passed |
| `uv run pytest -m db -q`（SQLite / MySQL 8.4 / PG 18 各一次） | passed，无新增 skip |
| `uv run pytest tests/integration/test_migrations.py -q`（三库） | upgrade→downgrade→upgrade 通过 |
| `CROSSERP_DATABASE_URL=sqlite:///tmp/t32.db uv run crosserp init`（第一次） | 提示建管理员，结束打印「数据库已就绪」 |
| 同上再跑一次 | 不提问，直接「数据库已就绪」 |
| `uv run crosserp audit verify` | 通过 |
| `uv run pytest --cov=crosserp --cov-fail-under=60` / `ruff` / `mypy` / `pre-commit` | 全过 |

## maken 人工验收清单
- [ ] 在一个新文件夹里：`$env:CROSSERP_DATABASE_URL="sqlite:///D:/crosserp-t32/data.db"`，然后 `uv run crosserp init`，按提示建一个管理员（比如 `maken`）。
- [ ] 再跑一次 `uv run crosserp init`，这次它不应该再问你建管理员。
- [ ] `uv run crosserp user list`：能看到你的账号，角色一栏有 5 个角色。
- [ ] `uv run crosserp user add --username op1 --role operator --as maken`，再 `user list` 能看到 op1。
- [ ] 用 DB Browser for SQLite 打开 data.db，看 `app_user` 表：密码那一列是一长串 `$argon2id$...`，看不出原密码。
- [ ] `uv run crosserp audit tail`：最后几条有「建用户」，操作者写的是你的用户名。

## 问题
- **Q1 ⚠ 待 maken 确认：新增依赖 `argon2-cffi>=25.1`。** 选项：A 加 argon2-cffi（实施方案原定，推荐）；B 只用标准库 `hashlib.scrypt`（不加依赖，但偏离实施方案）。推荐 A。
- **Q2 ⚠ 待 maken 确认：会话表名。** 实施方案写 `session`。选项：A 改叫 `user_session`（避免和 SQLAlchemy `Session`、各库保留字混淆，推荐）；B 照方案叫 `session`。推荐 A；这是新表，不涉及改已合并结构。
- **Q3 ⚠ 待 maken 确认：密码最短长度。** 选项：A 10 位（推荐）；B 8 位；C 12 位。
- **Q4 ⚠ 待 maken 确认：单人模式等系统设置存哪里。** 选项：A 新表 `app_setting`（网页可改、改动可审计，推荐）；B 放配置文件（T33 的 `config.py`），改了要重启。推荐 A。
- **Q5 ⚠ 待 maken 确认：用户表能不能物理删除。** 选项：A 不删，只停用（`is_active=false`），审计里的 UUID 永远能对上人（推荐）；B 允许删除。推荐 A。
- **Q6 ⚠ 待 maken 确认：demo 账号。** 选项：A 演示库自动建 `demo` 用户、随机密码只打印一次（推荐）；B 固定密码 `demo`（方便但不安全，只在 127.0.0.1 时可接受）。推荐 A。

## 完成记录
（代理填写：实际运行的命令 + 输出摘要 + 提交哈希；maken 填写验收日期）
