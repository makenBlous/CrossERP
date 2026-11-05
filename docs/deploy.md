# Docker Compose 部署

T52 提供本地构建的 CrossERP 镜像和三个数据库 profile。镜像只在本机使用，不推送到 GHCR、Docker Hub 或其他仓库。

## 准备配置

在仓库根目录执行：

```bash
cp deploy/.env.example deploy/.env
```

然后把 `deploy/.env` 中的密码全部改成自己的值。文件只在本机保存，不要提交。默认 URL 是推荐的 PostgreSQL profile；应用账号只用于业务读写，迁移账号只用于迁移和授权，智能体账号只读。

## 启动 PostgreSQL（推荐）

```bash
docker compose --profile pg up -d --build
curl -fsS http://127.0.0.1:8000/health
docker compose --profile pg exec app crosserp audit verify
```

健康检查应返回包含 `"status":"ok"` 的 JSON。停止并保留数据：

```bash
docker compose --profile pg down
docker compose --profile pg up -d
```

## 切换 MySQL 或 SQLite

先停止当前 profile，再把 `deploy/.env` 中三条 `CROSSERP_*_DATABASE_URL` 改为对应连接串。

MySQL：

```text
CROSSERP_DATABASE_URL=mysql+pymysql://crosserp_app:密码@mysql:3306/crosserp?charset=utf8mb4
CROSSERP_AGENT_DATABASE_URL=mysql+pymysql://crosserp_agent:密码@mysql:3306/crosserp?charset=utf8mb4
CROSSERP_MIGRATE_DATABASE_URL=mysql+pymysql://root:根密码@mysql:3306/crosserp?charset=utf8mb4
```

```bash
docker compose --profile mysql up -d --build
curl -fsS http://127.0.0.1:8000/health
```

SQLite：

```text
CROSSERP_DATABASE_URL=sqlite:////data/crosserp.db
CROSSERP_AGENT_DATABASE_URL=sqlite:////data/crosserp.db
CROSSERP_MIGRATE_DATABASE_URL=sqlite:////data/crosserp.db
```

```bash
docker compose --profile sqlite up -d --build
curl -fsS http://127.0.0.1:8000/health
```

Windows Docker Desktop 使用 PowerShell 时，把复制配置文件命令换成：

```powershell
Copy-Item deploy\.env.example deploy\.env
docker compose --profile pg up -d --build
curl.exe -f http://127.0.0.1:8000/health
```

## HTTPS 反向代理

`deploy/Caddyfile` 是示例配置。把 `CROSSERP_DOMAIN` 改成真实域名后，用 Caddy 代理到 `app:8000`，并保留 `CROSSERP_COOKIE_SECURE=1`。不要直接把应用端口暴露到公网；证书和 DNS 由部署方按自己的环境配置。

## 手动备份

项目不自动备份。停止服务后，按实际 profile 对命名卷做备份；SQLite 可以复制 `/data/crosserp.db`，PostgreSQL/MySQL 使用各自官方 dump 工具。
