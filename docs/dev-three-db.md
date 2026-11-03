# 三库本地验收

本项目的数据库测试使用当前项目目录下的 `.venv`。先在仓库根目录执行：

```bash
uv sync --locked --all-extras
```

有 Docker 时启动 MySQL 8.4 和 PostgreSQL 18：

```bash
bash scripts/dev/db-up.sh
```

PowerShell 使用：

```powershell
.\scripts\dev\db-up.ps1
```

等待两个容器健康后，分别设置连接串并运行同一套数据库测试：

```bash
CROSSERP_TEST_DATABASE_URL='mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4' \
  uv run pytest -m db -q
CROSSERP_TEST_DATABASE_URL='postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp' \
  uv run pytest -m db -q
```

PowerShell：

```powershell
$env:CROSSERP_TEST_DATABASE_URL = "mysql+pymysql://root:dev@127.0.0.1:13306/crosserp?charset=utf8mb4"
uv run pytest -m db -q
$env:CROSSERP_TEST_DATABASE_URL = "postgresql+psycopg://postgres:dev@127.0.0.1:15432/crosserp"
uv run pytest -m db -q
```

SQLite 不需要 Docker：

```bash
uv run pytest -m db -q
```

如果机器没有 Docker，跳过本地 MySQL/PostgreSQL，只看 CI 的 `db-matrix` 三个矩阵项；不要把连接失败当成测试通过。

数据库测试覆盖迁移往返、Money4 极值和 FxRate 精度、中文与 emoji、UTC 时间，以及合成样本导入的重复运行与异常断言。
