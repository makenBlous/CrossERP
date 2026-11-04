# 数据库

同一套代码连接 SQLite、MySQL 8.4 和 PostgreSQL 18。改连接串即可，业务代码不写原生 SQL。

金额列用 `Money4`（MySQL / PostgreSQL 为 DECIMAL(19,4)）。SQLite 没有精确小数，`Money4` 在 SQLite 上存整数万分位。汇率用 `FxRate`（DECIMAL(18,8)）。时间用 `UtcDateTime`，写入必须带时区，库存 UTC。超过允许小数位直接报错，不舍入。禁止 float。

本文件不建业务表。表结构在后续迁移任务里。

## W5 认证表

迁移 `0012_auth` 新增 `app_user`、`user_role`、`user_session`、`api_token` 和 `app_setting`。
密码列只保存 Argon2id 哈希；用户通过停用保留审计关联，不物理删除。`solo_mode` 设置保存在
`app_setting`，首次 `crosserp init` 创建管理员时默认设为 `true`。智能体账号不授予
`app_user`、`user_session`、`api_token` 的读取权限。

## 环境变量

| 变量 | 用途 |
|---|---|
| `CROSSERP_DATABASE_URL` | 应用连接串。未设置时使用 SQLite `~/.crosserp/data.db`，并自动创建 `~/.crosserp` 目录 |
| `CROSSERP_TEST_DATABASE_URL` | `pytest` 的 `engine` fixture。未设置时每个测试使用临时 SQLite 文件 |

切换数据库只改项目目录下的 `.env`，或设置同名环境变量。已有环境变量优先于 `.env`。`.env` 示例见仓库根目录的 `.env.example`。

PowerShell 也可以临时设置：`$env:CROSSERP_DATABASE_URL="..."`。

## SQLite

默认库，不用单独建库。第一次调用 `get_database_url()` 会创建目录，连接时创建文件。

```text
sqlite:///~/.crosserp/data.db
```

Windows 盘符路径可用。程序用 SQLAlchemy 的 URL 生成连接串，不手拼反斜杠。手写时用正斜杠：

```text
sqlite:///C:/Users/yourname/.crosserp/data.db
```

检查默认库：

```powershell
Remove-Item Env:CROSSERP_DATABASE_URL -ErrorAction SilentlyContinue
crosserp db check
```

## MySQL 8.4

要求：

- 服务器版本 ≥ 8.4。不支持 MySQL 8.0。
- 库字符集 `utf8mb4`，排序规则 `utf8mb4_0900_ai_ci`。
- `sql_mode` 包含 `STRICT_TRANS_TABLES`。非严格模式下超长或越界值可能被截断，金额不能接受。
- 连接串必须带 `charset=utf8mb4`。没有这一项时，引擎创建直接失败。

建库：

```sql
CREATE DATABASE crosserp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

库已经存在但字符集不对时：

```sql
ALTER DATABASE crosserp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

连接串：

```text
mysql+pymysql://user:password@127.0.0.1:3306/crosserp?charset=utf8mb4
```

PowerShell：

```powershell
$env:CROSSERP_DATABASE_URL = "mysql+pymysql://root:dev@127.0.0.1:3306/crosserp?charset=utf8mb4"
crosserp db check
```

通过时输出包含数据库类型、`MySQL 8.4.x`、`字符集 utf8mb4 OK` 和 `STRICT 模式 OK`。任一检查失败时退出码为 1，并打印中文修复提示。

本地 Docker（命令来自 `AGENTS.md` 第 7 节）：

```bash
docker run -d --name crosserp-mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=dev -e MYSQL_DATABASE=crosserp \
  mysql:8.4 --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci
```

驱动是 PyMySQL，装在 extra `mysql` 里。不要用 mysqlclient 或 mysql-connector。

## PostgreSQL 18

低于 18 只警告，不拒绝启动。

建库：

```sql
CREATE DATABASE crosserp;
```

连接前用 `SHOW server_encoding;` 确认编码是 `UTF8`。不要依赖数据库自带的全文检索或 PG 专属类型。

连接串：

```text
postgresql+psycopg://postgres:dev@127.0.0.1:5432/crosserp
```

PowerShell：

```powershell
$env:CROSSERP_DATABASE_URL = "postgresql+psycopg://postgres:dev@127.0.0.1:5432/crosserp"
crosserp db check
```

本地 Docker（命令来自 `AGENTS.md` 第 7 节）：

```bash
docker run -d --name crosserp-pg -p 5432:5432 -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=crosserp postgres:18
```

驱动是 psycopg 3，装在 extra `postgres` 里。

## 三库各跑一遍测试

未设置 `CROSSERP_TEST_DATABASE_URL` 时，下面的命令使用临时 SQLite 文件：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -m db -q
```

MySQL 8.4：

```powershell
$env:CROSSERP_TEST_DATABASE_URL = "mysql+pymysql://root:dev@127.0.0.1:3306/crosserp?charset=utf8mb4"
python -m pytest -m db -q
```

PostgreSQL 18：

```powershell
$env:CROSSERP_TEST_DATABASE_URL = "postgresql+psycopg://postgres:dev@127.0.0.1:5432/crosserp"
python -m pytest -m db -q
```

## 存储对照

| 类型 | MySQL | PostgreSQL | SQLite |
|---|---|---|---|
| `Money4` | `DECIMAL(19,4)` | `NUMERIC(19,4)` | `INTEGER` 万分位，上限 ±922337203685477.5807 |
| `FxRate` | `DECIMAL(18,8)` | `NUMERIC(18,8)` | `VARCHAR(32)`，存 Decimal 的固定小数字符串 |
| `UtcDateTime` | `DATETIME(6)`，无时区，存 UTC | `TIMESTAMP WITH TIME ZONE` | 无时区的 UTC 时间 |

读出的金额和汇率都是 `Decimal`。读出的时间都带 `UTC`。
