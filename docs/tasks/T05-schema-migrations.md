# T05 数据模型：v0.1 业务表 + Alembic 初始迁移 + upsert

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W1 | 2 天 | T04 | `task/T05-schema-migrations` |

## 目标
把 v0.1 需要的表用方言中立的方式建好，三库都能 `alembic upgrade head` / `downgrade base` 往返；提供 upsert 封装。

## 背景
- 实施方案 4（数据模型，字段以该表为准）、8 W1 第 4 条。
- 拆分说明（推断，按「每个任务 ≤2 天」拆）：本任务只建 v0.1 用到的表；`voucher`、`approval`、`app_user`、`llm_*` 等 v0.5 表在对应周的任务里用新迁移添加。若 maken 希望一次建全，改范围前先确认。

## 范围
- `core/enums.py`：`Platform`（amazon/shopify/lingxing/sellfox/other）、`ImportStatus`、`FeeCategory`（commission/fba/shipping/promotion/refund/ads/other + principal/shipping_charge，推断：6.4 伪代码用到）、`IssueKind`（6.1 全部 13 个原因码）、`IssueStatus`（open/explained/resolved/ignored）、`MatchStatus`（matched/partial）。用 `StrEnum`，数据库里存 `String(32)`，不用数据库原生 ENUM。
- `db/schema.py`（SQLAlchemy 2.x Declarative，`Mapped[...]`），表与字段严格按实施方案第 4 节：
  `import_batch`、`raw_row`、`store`、`sku`、`sku_cost`、`fx_rate`、`order_line`、`settlement`、`settlement_line`、`fee`、`match`、`issue`、`profit_snapshot`、`audit_log`、`audit_head`。
  - 主键：`Uuid`（Python 端 `uuid.uuid4` 生成）；`raw_row` 可用 BigInteger 自增（数量大，推断），需三库通过。
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
6. 三库各跑一次。

## 涉及文件
`src/crosserp/core/enums.py` `src/crosserp/core/models.py` `src/crosserp/db/schema.py` `src/crosserp/db/dialects.py` `src/crosserp/db/repo/*.py` `src/crosserp/db/migrations/**` `src/crosserp/cli.py` `tests/integration/test_migrations.py` `tests/integration/test_upsert.py` `tests/guard/test_schema_portable.py` `docs/architecture.md`（表清单一节） `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run crosserp init`（默认 SQLite） | 打印「数据库已就绪」；再运行一次仍成功 |
| 三库分别 `uv run pytest -m db -q` | 全部 passed（含迁移往返） |
| `uv run pytest tests/guard -q` | passed |
| `uv run alembic -c <配置> check`（或等价命令） | 模型与迁移无差异 |

## maken 人工验收清单
- [ ] 运行 `uv run crosserp init`，看到「数据库已就绪」。
- [ ] 用 MySQL 连接串（同 T04）再运行一次 `uv run crosserp init`，用 Navicat/DBeaver 打开 `crosserp` 库，能看到 `settlement`、`order_line`、`issue` 等表。
- [ ] 在表结构里看 `settlement.total` 列类型是 `decimal(19,4)`。
- [ ] 对照实施方案第 4 节，抽查 3 张表的字段名是否一致。

## 问题

## 完成记录
