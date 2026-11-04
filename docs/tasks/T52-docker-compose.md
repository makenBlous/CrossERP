# T52 Docker Compose 部署：SQLite / PostgreSQL / MySQL 三种 profile（不推镜像）（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W9 | 1.5 天 | T51 | `main` |

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
- **Q1 ⚠ 待 maken 确认：团队部署默认用哪个数据库。** 选项：A PostgreSQL（推荐，事务与 JSON 支持好，测试最全）；B MySQL（如果公司已有 MySQL 运维）；C 小团队继续 SQLite。
- **Q2 ⚠ 待 maken 确认：HTTPS 反向代理示例。** 选项：A Caddy（推荐，配置最少）；B Nginx；C 只写文字说明。

## 完成记录
（代理填写）
