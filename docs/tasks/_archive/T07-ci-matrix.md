# T07 CI：三系统 × Python 3.12/3.14 + 三数据库矩阵

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**
> **取代标注：** 旧任务把三库矩阵写成长期目标；已被 08 v4 第 11.3 节取代：MySQL 8.4 为正式目标，SQLite 为演示，PostgreSQL 仅在启用条件满足时验证。

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W1 | 1 天 | T05（T06 合并后 CI 也要绿） | `task/T07-ci-matrix` |

## 目标
每次推送和 PR，GitHub Actions 自动在 Windows/macOS/Linux 和 SQLite/MySQL 8.4/PostgreSQL 18 上跑全部检查；全绿才能合并。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 背景
- 实施方案 7.3、8 W1 第 8 条。

## 范围
- `.github/workflows/ci.yml`，触发：`push` 到 main、`pull_request`。
- job `lint`：ubuntu，`uv sync --locked --all-extras` → `ruff format --check` → `ruff check` → `mypy`。
- job `test`：矩阵 `os: [ubuntu-latest, windows-latest, macos-latest]` × `python: ["3.12", "3.14"]`，SQLite；`uv run pytest --cov=crosserp --cov-fail-under=60`。
- job `db-matrix`：ubuntu；`services`：
  - `mysql:8.4`，env `MYSQL_ROOT_PASSWORD`、`MYSQL_DATABASE=crosserp`，健康检查 `mysqladmin ping`；启动参数用 utf8mb4（通过 `options` 或测试前执行 `ALTER DATABASE`，代理自选可行方案并在 PR 说明）。
  - `postgres:18`，`POSTGRES_DB=crosserp`，健康检查 `pg_isready`。
  - 矩阵 `db: [sqlite, mysql, postgres]` 设置 `CROSSERP_TEST_DATABASE_URL`；跑 `pytest -m db` 和迁移往返（upgrade head → downgrade base → upgrade head）。
- 使用 `astral-sh/setup-uv` 官方 action（版本取当前最新主版本，PR 里写明）；开启 uv 缓存。
- `concurrency` 取消同分支旧运行；`permissions: contents: read`。
- CI 里的数据库密码只是测试容器用的占位值，**不得**使用任何真实密钥。
- README 加 CI 徽章。

## 不做
- 不做 release.yml、install-matrix.yml（W3/W9）。不配置分支保护（maken 在 GitHub 网页手动设置）。

## 步骤
1. 写 ci.yml。
2. 推到分支，开 PR，观察 Actions；修到全绿。常见问题：Windows 路径、换行、SQLite 文件锁。
3. 若某平台确实无法支持（例如 macOS 上某依赖），**不要删矩阵项**，停下来问。

## 涉及文件
`.github/workflows/ci.yml` `README.md` `CHANGELOG.md`；为修 CI 而改的代码需在 PR 里逐条说明。

## 验收标准
| 检查 | 期望 |
|---|---|
| PR 页面 Checks | lint 1 个 + test 6 个 + db-matrix 3 个，全部绿色 |
| db-matrix mysql 日志 | 能看到 `crosserp db check` 或测试输出里的 MySQL 版本 8.4.x |
| 覆盖率 | ≥60%，低于则 job 失败 |

## maken 人工验收清单
- [ ] 打开 GitHub 仓库的 Pull requests → 该 PR → Checks，数一下：共 10 个左右，全是绿勾。
- [ ] 点开 `db-matrix (mysql)`，搜索 `8.4`，能看到 MySQL 版本。
- [ ] 合并后，在 GitHub 仓库 Settings → Branches 给 `main` 加保护规则：要求以上检查通过才能合并（代理不能替你做这一步）。

## 问题

- 本机没有 Docker，没有 git remote，没有推送，没有开 PR，也没有 GitHub Actions 运行记录。不能声称 Checks 全绿。MySQL 8.4 和 PostgreSQL 18 的 job 已写在 workflow 里，供以后仓库和容器可用时使用。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- README 徽章里的 `OWNER` 是占位。使用说明建议仓库名 `crosserp`，但 GitHub 用户名未核实。建仓后把两处 URL 换成实际 `用户名或组织/crosserp`。
- `astral-sh/setup-uv` 从 v8 起不再发布浮动主版本标签。2026-10-28 最新主版本是 v10，最新发行版是 `v10.3.3`（commit `68559e99cc807c1eb7e9238fd43a15bba460eec2`）。workflow 钉在这个不可变标签，而不是不存在的 `@v10`。
- 本地 `ruff format --check` 和 `ruff check` 在既有文件上报错，不是本次改动引入的。未改那些文件。见完成记录。

## 完成记录

分支：`task/T07-ci-matrix`。未推送。状态改为 `review`，不是 `done`。未改 `docs/tasks/README.md`。

### MySQL utf8mb4

GitHub Actions 的 service `options` 是 `docker create` 旗标，不能把 `--character-set-server=utf8mb4` 传给 mysqld。因此没有用 options 冒充启动参数。

`db-matrix` 的 mysql 项在测试前用已安装的 PyMySQL 执行：

```sql
ALTER DATABASE crosserp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

这与 `docs/database.md` 和 `crosserp.db.dialects` 的修复提示一致。连接串带 `charset=utf8mb4`。若 `@@GLOBAL.sql_mode` 没有 `STRICT_TRANS_TABLES`，同一脚本会 `SET GLOBAL` 补上，否则 `crosserp db check` 会拒绝启动。MySQL 8.4 官方镜像默认通常已包含该模式；这一步是幂等保险。随后该矩阵项运行 `crosserp db check`，日志里应能搜到 `8.4`。本机没有容器，这段没有实跑。

密码 `dev` 与 `AGENTS.md` 本地 Docker 示例相同，只给 CI 测试容器用，不是真实密钥。

`postgres:18` 使用 `pg_isready` 健康检查。SQLite / MySQL / PostgreSQL 都跑 `pytest -m db`，并单独执行 `upgrade head` → `downgrade base` → `upgrade head`。服务容器挂在整个 `db-matrix` job 上，三个矩阵项都会启动这两个容器。GitHub Actions 不能按矩阵项关闭 service。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

### setup-uv 与 Python

- action：`astral-sh/setup-uv@v10.3.3`。uv 版本范围 `0.13.x`，解析策略用 action 默认的 highest。2026-10-26 该范围内最新是 uv 0.13.6。
- 开启 `enable-cache` 和 `cache-python`。
- checkout 用当前主版本 `actions/checkout@v7`。
- Python 写成 `3.12` 和 `3.14`，并设 `UV_PYTHON_PREFERENCE=only-managed`。装完后断言主次版本匹配，且 `releaselevel == final`。这样不会选用预发布解释器。
- 覆盖率门槛仍是 60，没有删测试，也没有降低门槛。

### 本地检查

2026-11-02，解释器 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`，版本 `3.14.10`。没有新建或删除虚拟环境。

| 命令 | 结果 |
|---|---|
| YAML 结构检查（PyYAML `safe_load`，核对触发、权限、concurrency、三个 job、矩阵、镜像、健康检查、覆盖率 60、utf8mb4、迁移往返，并编译内嵌 Python） | 退出码 0。`YAML_CHECK_OK` |
| `python -m ruff format --check .` | 退出码 1。`src/crosserp/db/migrations/env.py` 会被重排。该文件不在本次 diff 里，未改 |
| `python -m ruff check .` | 退出码 1。`src/crosserp/core/enums.py` 的 RUF002、`tests/guard/test_schema_portable.py` 的 RUF003。两处都不在本次 diff 里，未改 |

没有跑 GitHub Actions。没有编造 lint / test / db-matrix 的远程结果。
