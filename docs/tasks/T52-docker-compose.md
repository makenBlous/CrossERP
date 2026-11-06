# T52 Docker Compose 部署：SQLite / PostgreSQL / MySQL 三种 profile（不推镜像）（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| blocked | W9 | 1.5 天 | T51 | `main` |

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
- **Q3 阻塞，待 maken 决定：MySQL 8.4 迁移遇到已有字段不兼容。** `prompt_version.content` 当前是已合并的 `String(100000)`，MySQL 8.4 拒绝创建（单列上限 16383 字符），所以 MySQL profile 无法启动。
  - A（推荐）：把该字段改成三库都能存长文本的通用 `Text`，补一个迁移并重新跑三库往返；这会改已合并的数据库结构，需要 maken 明确同意。
  - B：保持现有结构，T52 暂时只验收 PostgreSQL/SQLite，把 MySQL 兼容修复另立任务；MySQL profile 继续不可用。
  - C：换成 MariaDB 或其他数据库绕开；会偏离固定技术栈，不推荐。
- Q3 已按 maken 选择 A：新增 0018，将 `prompt_version.content` 改为 `Text().with_variant(mysql.MEDIUMTEXT(), "mysql")`，只修改这一列；迁移前后正文和 sha256 保持不变。
- **Q4 阻塞，待 maken 决定：严格的 `String(n) <= 16383` 守卫与另外两列冲突。** 扫描发现 `llm_call.question_text`、`llm_call.answer_text` 都是 `String(1000000)`；它们不是本次批准修改的列。
  - A（推荐）：再批准一个后续迁移，把这两列也改成长文本类型；这样严格守卫和 MySQL 全量迁移都能通过。
  - B：暂不改这两列，守卫对这两个已知遗留列做明确例外；MySQL 全量迁移仍会在它们处失败。
  - C：不加严格守卫，保留现状；以后仍可能漏掉同类问题。

## 完成记录
- 当前状态：blocked，未提交正式 T52；已用 WIP 提交保存未完成改动。
- 已完成：Dockerfile、Compose 三 profile、非 root 运行、迁移/授权脚本、授权覆盖守卫、Caddy 示例和部署文档；新增 0018 提示词正文类型迁移。
- 已验证：SQLite 迁移/数据哈希测试 6 passed；PostgreSQL 迁移测试 5 passed、1 skipped（SQLite 专属断言）；PostgreSQL/SQLite profile 的 `/health` 和容器内 `crosserp audit verify` 均通过。
- MySQL 结果：修复 `prompt_version.content` 后，迁移继续执行到 `llm_call.question_text` 时失败；`answer_text` 同样是超长列。MySQL 端当前未通过。
- CI 原因：T16 的 MySQL 通过记录早于 T44 的 `0015_llm_observability` 迁移；现有 CI 会先执行迁移往返再跑测试，不会把迁移错误静默跳过。仓库没有 T44 之后 MySQL 迁移成功的可核实记录，因此之前没有拦住是覆盖范围/时点问题，不是把失败测试删掉。
- 待决：Q4 选择 A/B/C 后继续；当前未进入 T53。
