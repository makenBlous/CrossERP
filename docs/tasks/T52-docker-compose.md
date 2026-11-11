# T52 Docker Compose 部署：SQLite / PostgreSQL / MySQL 三种 profile（不推镜像）（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**
> **取代标注：** 旧任务把 SQLite、PostgreSQL、MySQL 三种 profile 写成并列部署目标；已被 08 v4 第 11.3 节取代：正式环境 MySQL 8.4，SQLite 演示，PostgreSQL 仅备选。

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W9 | 1.5 天 | T51 | `main` |

## 目标
团队部署时，一条 `docker compose --profile pg up -d` 就能起来：应用 + 数据库 + 只读账号 + 迁移；镜像只在本地构建，**不推到任何镜像仓库**。

## 背景
- 实施方案 8 W9 第 3 条；决定「v1.0 前不发布：不推 PyPI/GHCR」。
- 仓库现状：已有三库测试与 `scripts/sql/grant_*.sql`（逐表授权，新增表后必须重跑——W4 遗留风险）；`serve` 在 T33 后支持 `--host`（容器内需 0.0.0.0，且需 HTTPS 反向代理）。

## 范围
- `Dockerfile`（多阶段：uv 构建 wheel → slim 运行；非 root 用户；`HEALTHCHECK` 调 `/health`）。
- `docker-compose.yml` profiles：`sqlite`（数据卷）、`pg`（postgres 官方镜像，版本固定到小版本）、`mysql`；`migrate` 一次性服务：`crosserp init`（现有命令，含迁移，幂等；若迁移与建管理员需拆开，新增 `crosserp db upgrade` 子命令）→ 运行 grants 脚本 → 退出；`app` 依赖 migrate 成功。
- 反向代理示例 `deploy/Caddyfile`（Caddy 自动 HTTPS；只作示例，⚠ Q1）。
- 密码全部来自 `.env`（`deploy/.env.example`），不写死；`CROSSERP_COOKIE_SECURE=1`。
- `scripts/check_grants_cover_all_tables.py` + 测试：schema 中每张表都必须在 grants 脚本中出现（解决「新增表忘记授权」风险）。
- `docs/deploy.md`：Windows（Docker Desktop）步骤与 PowerShell 命令。
- 提交：`main`，`feat(deploy): add docker compose profiles (T52)`；测试不过不提交；**不推镜像、不发布**。

## 不做
- 不推 GHCR/Docker Hub；不做 Kubernetes；不做自动备份（文档给手动命令）。

## 步骤
1. 写 grants 覆盖测试（先失败再修脚本）。
2. 写 Dockerfile/compose；在本机三种 profile 各起一次，`curl /health` 200、登录页 200、`crosserp audit verify` 通过（容器内执行）。
3. 本机无 Windows/PowerShell：Windows 步骤标「未在本机验证，待 maken 验证」。

## 涉及文件
`Dockerfile` `.dockerignore` `docker-compose.yml` `deploy/{Caddyfile,.env.example}` `scripts/check_grants_cover_all_tables.py` `tests/guard/test_grants_cover_tables.py` `docs/deploy.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `docker compose --profile pg up -d --build && curl -fsS http://127.0.0.1:8000/health` | 200 |
| 同上 `--profile mysql`、`--profile sqlite` | 200 |
| `docker compose --profile pg exec app crosserp audit verify` | 通过 |
| `uv run pytest tests/guard -q` | passed |

## maken 人工验收清单
- [ ] 装好 Docker Desktop，在仓库目录 PowerShell 里：`Copy-Item deploy\.env.example deploy\.env`，打开 `deploy\.env` 改密码。
- [ ] `docker compose --profile pg up -d --build`，浏览器打开 http://127.0.0.1:8000 能看到登录页。
- [ ] `docker compose --profile pg down` 再 `up -d`：数据还在。

## 问题
- Q1 按推荐默认使用 PostgreSQL；Q2 按推荐默认使用 Caddy。
- Q3 已按 maken 选择 A：新增 0018，将 `prompt_version.content` 改为 `Text().with_variant(mysql.MEDIUMTEXT(), "mysql")`，只修改这一列；迁移前后正文和 sha256 保持不变。
- **Q4 已按 maken 决定 A：** `llm_call.question_text`、`llm_call.answer_text` 也改成长文本，严格守卫不留例外。

## 完成记录
- 完成内容：Dockerfile、Compose 三 profile、非 root 运行、迁移/授权脚本、授权覆盖守卫、Caddy 示例和部署文档；0018 将 `prompt_version.content`、0019 将 `llm_call.question_text/answer_text` 改为 `Text().with_variant(mysql.MEDIUMTEXT(), "mysql")`；新增严格 `String(n) <= 16383` 守卫；授权模板补充 `alembic_version` 最小读权限。
- 修改文件：`Dockerfile`、`.dockerignore`、`docker-compose.yml`、`deploy/Caddyfile`、`deploy/.env.example`、`docs/deploy.md`、`scripts/docker-init.sh`、`scripts/render_grant_sql.py`、`scripts/check_grants_cover_all_tables.py`、`scripts/sql/grant_mysql.sql`、`scripts/sql/grant_pg.sql`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0015_llm_observability.py`、`src/crosserp/db/migrations/versions/0018_prompt_content_text.py`、`src/crosserp/db/migrations/versions/0019_llm_text_columns.py`、相关测试和 `CHANGELOG.md`。
- 数据与哈希：SQLite、PostgreSQL 18、MySQL 8.4 均实际执行升级/回退/再升级；提示词正文、`sha256`、问答正文均原样保留。MySQL 回退保留 `MEDIUMTEXT`，因为历史 `VARCHAR(100000/1000000)` 在 MySQL 8.4 本身不可创建；版本可以回退且数据库保持可用。
- 三库迁移测试：SQLite 7 passed；PostgreSQL 18 为 6 passed、1 skipped；MySQL 8.4 为 6 passed、1 skipped。
- Compose 验证：三个 profile 的镜像均本地构建；PostgreSQL、MySQL、SQLite 的 `/health` 返回 `status: ok`，容器内 `crosserp audit verify` 均输出“审计链完整：1 条”。MySQL profile 使用 8.4.6，迁移账号、应用账号和只读账号均可用。
- 守卫与静态检查：授权覆盖测试 2 passed；`tests/guard` 19 passed；ruff、mypy、pre-commit 全部通过。
- MySQL CI 原因与修复：T16 的 MySQL 通过记录早于 T44 的 `0015_llm_observability` 迁移；之后没有可核实的 T44+ MySQL 绿色记录，且本地此前只验证了 SQLite/旧迁移状态，所以 `String(100000)` 和 `String(1000000)` 未被发现。修复方式是把新建表迁移和后续增量迁移都改为 `Text + MEDIUMTEXT`，加入无例外长度守卫，并真实运行 MySQL 8.4 全量迁移和 Compose profile；同时修正 0015 回退的外键索引删除顺序。
- 后续约定：以后同类超长 VARCHAR 改长文本的问题，直接按本次 Text + MySQL MEDIUMTEXT 方案处理，不再重复询问。
