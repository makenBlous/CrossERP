# T16 三库实测：CI db-matrix 在 MySQL 8.4 / PostgreSQL 18 跑通

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1 天 | T07, T13 | `task/T16-three-db-verify` |

## 目标
把 T01–T14 在 MySQL 8.4 和 PostgreSQL 18 上**真正跑一遍**，修掉暴露的问题，留下证据。之后所有任务都在三库绿灯的基础上做。

## 背景
- maken 的 T01–T14 本地验收**只用了 SQLite**（.venv），MySQL 和 PostgreSQL 没跑过。
- 实施方案 7.3（CI db-matrix：mysql:8.4、postgres:18 服务容器 + 迁移往返）；新增验收项 A「三库：SQLite / MySQL 8.4 / PostgreSQL 18 跑同一套测试全绿，金额往返无精度损失，中文/emoji 无乱码」（v0.1，待 maken 确认的新增项）。
- T07 写了 workflow，但是否在 GitHub 上真的跑过、是否全绿，**未核实**。

## 范围
1. 在 GitHub Actions 上看 `ci.yml` 最近一次 main 的运行：`lint`、`test`（3 系统 × 2 Python）、`db-matrix`（3 库）各 job 结果。没跑过或失败 → 修。
2. 本地复现（给 maken 用）：新增 `scripts/dev/db-up.ps1` 和 `scripts/dev/db-up.sh`（`docker run` 起 `mysql:8.4`、`postgres:18`，端口 13306/15432，密码只是本地占位值），以及 `docs/dev-three-db.md`（PowerShell 命令：设置 `CROSSERP_TEST_DATABASE_URL` → `uv run pytest -m db -q`）。没有 Docker 的机器上写明「跳过本地，只看 CI」。
3. 必须覆盖的检查（缺的补测试，`-m db`）：
   - 迁移往返 upgrade head → downgrade base → upgrade head。
   - Money4 往返：`0.0001`、`-0.0001`、`922337203685477.5807`、`-922337203685477.5807`、`123456789.1234` 存进去读出来完全相等；FxRate `7.12345678` 往返相等。
   - 中文 + emoji（`保温杯 🍵 黑色 500ml`）存取一致（MySQL 必须 utf8mb4）。
   - MySQL 会话 `sql_mode` 含 `STRICT_TRANS_TABLES`（T04 自检）。
   - T13 端到端：demo-import 两遍、`SETTLEMENT_UNBALANCED` 恰好 1 条，在三库上结果完全一样（同一套断言）。
   - 时间列往返保持 UTC（PG `timestamptz`、MySQL `DATETIME(6)` 方案以 T04 为准）。
4. 证据：`docs/evidence/three-db-<YYYY-MM-DD>.md`：CI 运行链接、每库通过的测试数、发现并修复的问题列表。
5. 在 GitHub 仓库设置里开分支保护（实施方案 7.3 要求 CI 绿才能合并）——**代理只写操作说明，由 maken 在网页上点**。

## 不做
- 不新增功能；只修三库暴露的 bug。修复如需改表结构，新建迁移，不改旧迁移。
- 不把真实密码写进仓库或 workflow。

## 步骤
1. 先查 CI 历史，把每个失败 job 的报错摘要写进 PR。
2. 补缺失的三库测试（上面第 3 条），本地或 CI 上跑出失败 → 修。
3. 写脚本和 dev 文档、证据文件。

## 涉及文件
`.github/workflows/ci.yml` `scripts/dev/db-up.ps1` `scripts/dev/db-up.sh` `docs/dev-three-db.md` `docs/evidence/three-db-*.md` `tests/integration/test_three_db_roundtrip.py`；修 bug 时涉及的 `src/crosserp/db/*`（PR 里逐条说明）

## 验收标准（代理自测，全部要实际跑）
| 命令 / 检查 | 期望 |
|---|---|
| GitHub Actions `ci.yml` 在本分支 | lint、test 6 格、db-matrix 3 格全绿 |
| CI 日志里 db-matrix mysql 格 | 能看到迁移往返和 `-m db` 的测试数，跳过数为 0（不能因为连不上库全部 skip） |
| `uv run pytest -m db -k roundtrip -q`（三库） | passed |

## maken 人工验收清单
- [ ] 打开 PR 的 Checks 页，确认 db-matrix 的 mysql、postgres 两格是绿的，点进去看 pytest 汇总行里 **skipped 不是全部**。
- [ ] （有 Docker Desktop 时）按 `docs/dev-three-db.md` 在本机跑一次 MySQL，截图 pytest 汇总行。
- [ ] 在 GitHub 仓库 Settings → Branches 给 main 开保护，要求 CI 通过（按代理写的步骤）。

## 问题

- GitHub Actions 上一轮 main 运行（[CI #2](https://github.com/makenBlous/CrossERP/actions/runs/41567272614)）的公开 API 显示 lint、6 个 test、3 个 db-matrix job 全部失败；未授权读取 job 日志返回 403，因此不能编造每个 job 的具体错误。当前分支尚未推送，未产生本分支 Checks 结果。
- `samples/real_anonymized/` 未提供，现有真实文件试导入测试按约定跳过 1 项；三库主测试均实际连接并通过，不是连接失败导致跳过。
- 本机没有 PowerShell，`scripts/dev/db-up.ps1` 只做了人工代码检查，未在 PowerShell 解释器执行。

## 完成记录

分支：`task/T16-three-db-verify`。状态改为 `review`，不是 `done`。

### 做了什么

- 增加 `tests/integration/test_three_db_roundtrip.py`，覆盖迁移往返、Money4 五个边界值、FxRate 八位小数、中文和 emoji、UTC 时间；三库均为 6 passed。
- 增加 `scripts/dev/db-up.sh`、`scripts/dev/db-up.ps1` 和 `docs/dev-three-db.md`，固定使用项目 `.venv`、MySQL 8.4 端口 13306、PostgreSQL 18 端口 15432，并说明无 Docker 时只看 CI。
- 增加 `docs/evidence/three-db-2026-11-03.md`，记录真实版本、自检、三库测试数和上一轮 CI 运行链接。
- 增加 `tests/__init__.py`，修复 Python 3.14 下外部同名 `tests` 包导致的测试收集失败。
- 修复初始迁移 downgrade 先删外键再删索引，使 MySQL 8.4 的 `upgrade head → downgrade base → upgrade head` 可执行；没有改变表字段或新增迁移。
- 按 ruff 规则格式化既有文件，并修正既有中文标点 lint 报错，使项目全量 lint 通过。

### 实际验收命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest --cov=crosserp --cov-fail-under=60 -q` | 181 passed, 2 skipped；覆盖率 85.82% |
| `CROSSERP_TEST_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4 uv run pytest -m db -q` | 90 passed, 3 skipped；MySQL 8.4.13 |
| `CROSSERP_TEST_DATABASE_URL=postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp uv run pytest -m db -q` | 89 passed, 4 skipped；PostgreSQL 18.6 |
| `uv run pytest -m db -q` | 91 passed, 2 skipped；SQLite |
| `uv run ruff format --check . && uv run ruff check .` | 全部通过 |
| `uv run mypy` | `Success: no issues found in 49 source files` |
| `uv run pre-commit run --all-files` | ruff-format、ruff、mypy 全部 Passed |
| `bash -n scripts/dev/db-up.sh` | 通过 |

### 偏离计划

- `.github/workflows/ci.yml` 未改动；现有 workflow 已包含目标矩阵。由于本任务分支未推送，不能声称本分支 GitHub Checks 已绿；本地三库结果已真实跑通。
- GitHub 分支保护只写入人工验收清单，未通过网页设置。
