# T05 数据模型：v0.1 业务表 + Alembic 初始迁移 + upsert

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W1 | 2 天 | T04 | `task/T05-schema-migrations` |

## 目标
把 v0.1 需要的表用方言中立的方式建好，三库都能 `alembic upgrade head` / `downgrade base` 往返；提供 upsert 封装。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 背景
- 实施方案 4（数据模型，字段以该表为准）、8 W1 第 4 条。
- 拆分说明（推断，按「每个任务 ≤2 天」拆）：本任务只建 v0.1 用到的表；`voucher`、`approval`、`app_user`、`llm_*` 等 v0.5 表在对应周的任务里用新迁移添加。若 maken 希望一次建全，改范围前先确认。

## 范围
- `core/enums.py`：`Platform`（amazon/shopify/lingxing/sellfox/other）、`ImportStatus`、`FeeCategory`（commission/fba/shipping/promotion/refund/ads/other + principal/shipping_charge，推断：6.4 伪代码用到）、`IssueKind`（6.1 全部 13 个原因码）、`IssueStatus`（open/explained/resolved/ignored）、`MatchStatus`（matched/partial）。用 `StrEnum`，数据库里存 `String(32)`，不用数据库原生 ENUM。
- `db/schema.py`（SQLAlchemy 2.x Declarative，`Mapped[...]`），表与字段严格按实施方案第 4 节：
  `import_batch`、`raw_row`、`store`、`sku`、`sku_cost`、`fx_rate`、`order_line`、`settlement`、`settlement_line`、`fee`、`match`、`issue`、`profit_snapshot`、`audit_log`、`audit_head`。
  - 主键：`Uuid`（Python 端 `uuid.uuid4` 生成）；`raw_row` 可用 BigInteger 自增（数量大，推断），需三库通过。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
  - 金额列全部 `Money4`；汇率 `FxRate`；时间 `UtcDateTime`；JSON 列用 `JSON`。
  - 唯一约束：`import_batch.file_sha256`；`sku(store_id, platform_sku)`；`fx_rate(period, from_ccy, to_ccy)`；`settlement(platform, external_id)`。
  - 索引字符串列长度 ≤255；`settlement_line(order_id, sku)` 联合索引总长度 ≤ 3072 字节。
  - `core/models.py`：对应的 Pydantic 模型（导入层用），与 ORM 分开。
- Alembic：`db/migrations/`，`env.py` 读 `CROSSERP_DATABASE_URL`；初始迁移 `0001_initial`（autogenerate 后**人工检查**，确保无方言专属类型）。`render_as_batch=True` 以兼容 SQLite。
- `db/dialects.py`：`upsert(session, table, values, conflict_cols, update_cols)`：MySQL `insert().on_duplicate_key_update()`；PG/SQLite `insert().on_conflict_do_update()`。
- CLI：`crosserp init` = 建库目录 + `alembic upgrade head` + 自检，重复执行无副作用。
- `db/repo/`：先放 `stores.py`、`fx.py` 两个最小 repo 作为样例（get/upsert）。

## 不做
- 不建 v0.5 表；不写导入逻辑；不做数据库授权脚本。

## 步骤
1. 写 enums、schema、models。
2. `alembic init` 到 `src/crosserp/db/migrations`，配置 `script_location` 使打包后 `crosserp init` 可用（`alembic.ini` 放包内或用程序化 `Config`）。
3. autogenerate 初始迁移，人工审查并改正。
4. 写 upsert 和 repo 样例。
5. 测试：
   - `tests/integration/test_migrations.py`（`db` marker）：upgrade head → 检查 15 张表存在 → downgrade base → 表全没了 → 再 upgrade head。
   - `tests/integration/test_upsert.py`：同一 `fx_rate(period, from, to)` upsert 两次，只有 1 行且 rate 是第二次的值。
   - `tests/guard/test_schema_portable.py`：遍历 `Base.metadata`，断言无 `ARRAY/JSONB`、所有 `String` 都有 length、建索引的 String length ≤255、所有名称含 `amount/total/price/cost/fee/profit/revenue` 的列类型是 `Money4`。
6. 三库各跑一次。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

## 涉及文件
`src/crosserp/core/enums.py` `src/crosserp/core/models.py` `src/crosserp/db/schema.py` `src/crosserp/db/dialects.py` `src/crosserp/db/repo/*.py` `src/crosserp/db/migrations/**` `src/crosserp/cli.py` `tests/integration/test_migrations.py` `tests/integration/test_upsert.py` `tests/guard/test_schema_portable.py` `docs/architecture.md`（表清单一节） `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run crosserp init`（默认 SQLite） | 打印「数据库已就绪」；再运行一次仍成功 |
| 三库分别 `uv run pytest -m db -q` | 全部 passed（含迁移往返） |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| `uv run pytest tests/guard -q` | passed |
| `uv run alembic -c <配置> check`（或等价命令） | 模型与迁移无差异 |

## maken 人工验收清单
- [ ] 运行 `uv run crosserp init`，看到「数据库已就绪」。
- [ ] 用 MySQL 连接串（同 T04）再运行一次 `uv run crosserp init`，用 Navicat/DBeaver 打开 `crosserp` 库，能看到 `settlement`、`order_line`、`issue` 等表。
- [ ] 在表结构里看 `settlement.total` 列类型是 `decimal(19,4)`。
- [ ] 对照实施方案第 4 节，抽查 3 张表的字段名是否一致。

## 问题

当前本地验收只跑 SQLite。MySQL 8.4 和 PostgreSQL 18 的 `pytest -m db`、`crosserp init` 没有实跑。本机没有可用的 MySQL / PostgreSQL。没有编造三库输出。代码仍按三库兼容写。配置文件里的 `CROSSERP_DATABASE_URL` 指向它们之后再补验收。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

以下是推断。没有停下来问。若不同意请改：

- `ImportStatus` 取值是 `running` / `done` / `failed`。任务文件没有列值。按 T09 导入流程推断。
- `match.settlement_line_id` 可空。实施方案写「settlement_line_id(或组)」。没有另建组表。
- `sku_cost.source_batch_id`、`deposit_date`、`order_line.item_price`、`profit_snapshot.ads` 等可空。实施方案没有写空值规则。
- `raw_row.id` 在 SQLite 上用 `Integer`。只有 INTEGER PRIMARY KEY 会自增。MySQL / PostgreSQL 仍是 BIGINT。迁移写的是 `BigInteger().with_variant(Integer(), "sqlite")`。不是方言专属类型类。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 守卫测试里 `amount_type`、`amount_description`、`fee_category` 名字含 amount/fee。但它们不是金额列。测试把这三列排除。其余含这些词的列必须是 Money4。

## 完成记录

当前分支 `task/T05-schema-migrations`。未推送。未把状态改成 done。未改 `docs/tasks/README.md`。

2026-11-02 在本 worktree 实际运行。解释器 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。未使用 `uv run`。未创建或删除虚拟环境。`PYTHONPATH` 指向本 worktree 的 `src`。

| 命令 | 结果 |
|---|---|
| `python -m pytest -q`（未设置 `CROSSERP_TEST_DATABASE_URL`。SQLite） | 退出码 0。`77 passed, 1 skipped, 1 warning in 3.31s`。跳过的是没有 MySQL 的自检测试 |
| `python -m pytest -m db -q` | 退出码 0。`40 passed, 1 skipped, 34 deselected, 1 warning in 2.49s` |
| `python -m pytest tests/guard -q` | 退出码 0。`9 passed in 0.18s` |
| `python -m pytest --cov=crosserp --cov-fail-under=60 -q` | 退出码 0。覆盖率 89.53%。`77 passed, 1 skipped, 1 warning in 3.31s` |
| `python -m crosserp.cli init`（未设置 `CROSSERP_DATABASE_URL`。默认 `~/.crosserp/data.db`） | 退出码 0。打印「数据库已就绪」 |
| 再运行一次 `python -m crosserp.cli init` | 退出码 0。仍打印「数据库已就绪」 |
| `alembic -c src/crosserp/db/alembic.ini check` | 退出码 0。`No new upgrade operations detected.` |
| `ruff check .` | 退出码 0。All checks passed |
| `mypy` | 退出码 0。Success: no issues found in 29 source files |

`crosserp init` 第一次输出：

```text
数据库类型: SQLite
版本: 3.53.1
自检: OK
数据库已就绪
```

第二次输出相同。

另外改了 `docs/database.md` 一行。原文写「本文件不建业务表」。现在改为指向 `docs/architecture.md` 的表清单。
