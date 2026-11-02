# T04 数据库层：Money4 / FxRate / UtcDateTime 类型 + 连接会话 + MySQL 启动自检

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W1 | 1.5 天 | T03 | `task/T04-db-types-session` |

## 目标
同一份代码连 SQLite / MySQL 8.4 / PostgreSQL 18，金额写进去读出来逐位相等，中文和 emoji 不乱码；MySQL 配置不对时拒绝启动并告诉用户怎么改。

## 背景
- 实施方案 4（金额规则 + 三库通用规则）、8 W1 第 3、5 条、7.4（MySQL 连接串示例）。
- SQLite 的 NUMERIC 会转成整数或浮点存（https://www.sqlite.org/datatype3.html），所以 SQLite 上 Money4 存整数万分位。
- MySQL utf8mb4：https://dev.mysql.com/doc/refman/8.4/en/charset-unicode-utf8mb4.html

## 范围
- `db/types.py`（SQLAlchemy `TypeDecorator`，`cache_ok = True`）：
  - `Money4`：`load_dialect_impl` → MySQL/PG 用 `Numeric(19, 4, asdecimal=True)`，SQLite 用 `BigInteger`；
    写入：只接受 `Decimal`（float → `TypeError`），小数位 > 4 → `PrecisionError`（不偷偷舍入），超出 DECIMAL(19,4) 范围 → `PrecisionError`；SQLite 写 `int(value * 10000)`（注意：SQLite INTEGER 是 64 位，万分位存储的上限是 ±922337203685477.5807，超出也抛 `PrecisionError`，并写测试）；
    读出：一律 `Decimal`，SQLite 用 `Decimal(v).scaleb(-4)`，统一 `quantize(Decimal("0.0001"))`。
  - `FxRate`：MySQL/PG `Numeric(18, 8)`；SQLite 存 `String(32)`（Decimal 的规范字符串）；小数位 > 8 → `PrecisionError`。
  - `UtcDateTime`：写入要求 tz-aware（naive → `ValueError`），转 UTC 后存（MySQL/SQLite 存 naive UTC，PG 用 `DateTime(timezone=True)`）；读出一律 `tzinfo=UTC`。
- `db/session.py`：
  - `get_database_url()`：读 `CROSSERP_DATABASE_URL`，默认 `sqlite:///<home>/.crosserp/data.db`（自动建目录；Windows 路径要能用）。
  - `make_engine(url)`：SQLite 打开 `PRAGMA foreign_keys=ON`；MySQL 若 URL 无 `charset=utf8mb4` → 报错提示。
  - `session_scope()` 上下文管理器（提交/回滚）。
- `db/dialects.py`：`check_server(engine)` 启动自检（只对 MySQL）：`SELECT VERSION()` ≥ 8.4；`SELECT @@character_set_database` = `utf8mb4`；`SELECT @@sql_mode` 含 `STRICT_TRANS_TABLES`。任一不满足抛 `DatabaseConfigError`，消息为中文修复提示（例：「请执行 ALTER DATABASE crosserp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;」）。PG 检查版本 ≥18 只给警告。
- `tests/conftest.py`：fixture `engine`，读 `CROSSERP_TEST_DATABASE_URL`，未设置时用 `tmp_path` 下的 SQLite 文件；每个测试建临时表、结束后 drop。
- `crosserp db check` CLI：打印数据库类型、版本、自检结果。

## 不做
- 不建业务表（T05）。不做 upsert（T05）。不做数据库账号授权脚本（W4）。

## 步骤
1. 写 types.py，先写测试再实现（`tests/integration/test_db_types.py`，标 `@pytest.mark.db`）：
   - `Decimal("12345678.1234")`、`Decimal("-0.0001")`、`Decimal("0")`、`Decimal("99999999999999.9999")` 写入读出完全相等（`==` 且 `str()` 相同的 4 位小数）；
   - `Decimal("1.23456")` 写入抛 `PrecisionError`；`1.5`（float）抛 `TypeError`；
   - FxRate `Decimal("7.12345678")` 往返相等；
   - UtcDateTime：北京时间 `2026-11-09 08:00+08:00` 读出等于 `2026-11-09 00:00Z`；
   - `String(255)` 列写入 `"保温杯 🍵 黑色"` 读出相等。
2. hypothesis 性质测试：任意 4 位小数 Decimal 在 SQLite 上往返相等（`tests/property/test_money4_sqlite.py`）。
3. 写 session.py、dialects.check_server、CLI。
4. 本地用 Docker 起 MySQL 8.4 和 PG 18（命令见 AGENTS.md 第 7 节），三库各跑一次 `pytest -m db`。
5. 写一个 MySQL 自检失败的测试：对 `latin1` 字符集的库（测试里 `CREATE DATABASE ... CHARACTER SET latin1`）调用 `check_server` 应抛 `DatabaseConfigError`；没有 MySQL 时 skip。

## 涉及文件
`src/crosserp/db/types.py` `src/crosserp/db/session.py` `src/crosserp/db/dialects.py` `src/crosserp/core/errors.py` `src/crosserp/cli.py` `tests/conftest.py` `tests/integration/test_db_types.py` `tests/integration/test_mysql_selfcheck.py` `tests/property/test_money4_sqlite.py` `docs/database.md`（新建：三库连接串、建库语句） `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest -m db -q`（SQLite 默认） | 全部 passed |
| 设 `CROSSERP_TEST_DATABASE_URL` 为 MySQL 8.4 后 `uv run pytest -m db -q` | 全部 passed |
| 设为 PostgreSQL 18 后 `uv run pytest -m db -q` | 全部 passed |
| `CROSSERP_DATABASE_URL=mysql+pymysql://root:dev@127.0.0.1:3306/crosserp?charset=utf8mb4 uv run crosserp db check` | 打印 `MySQL 8.4.x`、字符集 utf8mb4、STRICT 模式 OK |
| `uv run mypy` | 无错误 |

## maken 人工验收清单
- [ ] 本机装好 Docker Desktop（或 MySQL 8.4），按 AGENTS.md 第 7 节命令启动 MySQL。
- [ ] PowerShell：`$env:CROSSERP_DATABASE_URL="mysql+pymysql://root:dev@127.0.0.1:3306/crosserp?charset=utf8mb4"`，再运行 `uv run crosserp db check`，三项都显示 OK。
- [ ] 运行 `$env:CROSSERP_TEST_DATABASE_URL=$env:CROSSERP_DATABASE_URL; uv run pytest -m db -q`，全部通过。
- [ ] 用 MySQL 客户端（如 Navicat / DBeaver）看测试留下的数据（如果代理提供了演示脚本）：中文和 emoji 显示正常。

## 问题
- maken 于 2026-11-02 决定：当前本地验收只跑 SQLite。切换 MySQL / PostgreSQL 只改配置文件里的 `CROSSERP_DATABASE_URL`，不改业务代码。本机没有 Docker，不在这次验收里实跑 MySQL / PostgreSQL。代码仍保持三库兼容。

## 完成记录
