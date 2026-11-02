# 架构

## 表清单

v0.1 业务表在 `src/crosserp/db/schema.py`。字段以实施方案第 4 节为准。分类字段存 `String(32)`，不用数据库原生 ENUM。金额列是 `Money4`，汇率是 `FxRate`，时间是 `UtcDateTime`，JSON 用通用 `JSON`。主键是应用生成的 `Uuid`，`raw_row.id` 用自增 `BigInteger`。

不建 v0.5 的 `voucher`、`approval`、`app_user`、`security_event`、`llm_*` 等表。

| 表 | 字段 | 说明 |
|---|---|---|
| `import_batch` | id, connector_id, connector_version, file_name, file_sha256, imported_at, row_count, status, error_count | `file_sha256` 唯一。同一文件重复导入会被拒绝 |
| `raw_row` | id, batch_id, row_no, payload_json | 原样保留。id 自增。SQLite 上是 INTEGER PRIMARY KEY。MySQL / PostgreSQL 是 BIGINT |
| `store` | id, platform, marketplace, name, currency | 店铺。platform 为 amazon/shopify/lingxing/sellfox/other |
| `sku` | id, store_id, platform_sku, internal_sku, title, active | 唯一约束 `(store_id, platform_sku)` |
| `sku_cost` | id, internal_sku, valid_from, valid_to, unit_cost, currency, freight_per_unit, source_batch_id | 成本按生效期。`valid_to` 可空 |
| `fx_rate` | id, period, from_ccy, to_ccy, rate, source | 唯一约束 `(period, from_ccy, to_ccy)`。rate 为 `FxRate` |
| `order_line` | id, store_id, platform_order_id, order_item_id, platform_sku, qty, order_date, item_price, currency, source_batch_id, raw_row_id | `item_price` 可空 |
| `settlement` | id, store_id, platform, external_id, period_start, period_end, deposit_date, total, currency, source_batch_id | 唯一约束 `(platform, external_id)`。`deposit_date` 可空 |
| `settlement_line` | id, settlement_id, transaction_type, order_id, order_item_code, sku, qty, amount_type, amount_description, amount, posted_at, raw_row_id | `(order_id, sku)` 联合索引。字符串长度按 utf8mb4 不超过 3072 字节 |
| `fee` | id, settlement_line_id, fee_category, amount | fee_category 含 commission/fba/shipping/promotion/refund/ads/other/principal/shipping_charge |
| `match` | id, settlement_line_id, order_line_id, rule_id, status, diff, matched_at | `settlement_line_id` 可空，表示组级匹配。推断，未另建组表 |
| `issue` | id, kind, severity, settlement_line_id, order_line_id, detail_json, status, resolution_note, created_at | kind 为实施方案 6.1 的 13 个原因码。关联列可空 |
| `profit_snapshot` | id, period, internal_sku, store_id, revenue, fees, refunds, cogs, freight, ads, profit, currency, calc_version, inputs_hash | `ads` 可空，表示未含广告 |
| `audit_log` | id, ts, actor_type, actor_user_id, actor_role, action, target_type, target_id, before_json, after_json, approval_id, approver_id, reason, request_id, ip, user_agent, self_approved, prev_hash, hash | 只追加。approval 与用户表尚未建立，这两列不做外键 |
| `audit_head` | id, chain, last_id, last_hash | `chain` 唯一。空链时 last_id 与 last_hash 为空 |

切换 SQLite / MySQL / PostgreSQL 只改 `CROSSERP_DATABASE_URL`。`crosserp init` 会创建 SQLite 目录、执行 `alembic upgrade head` 并做启动自检。
