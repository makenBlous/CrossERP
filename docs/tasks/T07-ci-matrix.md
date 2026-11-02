# T07 CI：三系统 × Python 3.12/3.14 + 三数据库矩阵

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W1 | 1 天 | T05（T06 合并后 CI 也要绿） | `task/T07-ci-matrix` |

## 目标
每次推送和 PR，GitHub Actions 自动在 Windows/macOS/Linux 和 SQLite/MySQL 8.4/PostgreSQL 18 上跑全部检查；全绿才能合并。

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

## 完成记录
