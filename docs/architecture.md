# 架构

## 表清单

业务表和 W5–W10 内部功能表都在 `src/crosserp/db/schema.py`，由 Alembic 迁移管理。分类字段存 `String(32)`，不用数据库原生 ENUM。金额列是 `Money4`，汇率是 `FxRate`，时间是 `UtcDateTime`，JSON 用通用 `JSON`。主键是应用生成的 `Uuid`，`raw_row.id` 用自增 `BigInteger`。长文本使用通用 `Text`，MySQL 使用 `MEDIUMTEXT` variant。

当前实现包括审批、凭证草稿、认证、安全事件、AI 调用记录、预算和评测记录。写账仍只能从审批进入唯一写出口；AI 旁路只读。

| 表 | 字段 | 说明 |
|---|---|---|
| `import_batch` | id, connector_id, connector_version, file_name, file_sha256, imported_at, row_count, status, error_count | 只有成功批次按 sha256 拒绝重复。失败可重导。打不开时 sha256 留空 |
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

## 连接器与导入

文件导入器实现 `FileConnector`。`sniff` 给 0 到 1 的识别分，`read` 按原始行号读出字符串，`normalize` 把一行变成标准记录。标准记录是结算头、结算明细、订单、成本、汇率、异常之一。每条带 provenance：连接器 id、版本、批次 id、源文件、行号。数据库里用 `source_batch_id` 和 `raw_row_id` 把标准行指回原始行。

`ApiConnector` 只定义只读拉取，v0.1 不实现。`LedgerTarget` 只放类型定义。v0.5 由 ledger.write_service 使用。

注册表读 entry point 组 `crosserp.connectors`。内置连接器也在 `pyproject.toml` 注册。`detect` 取最高分。最高分低于 0.5，或最高分并列，就报错，并提示用 `--type` 指定。命令行导入本身在 T13。

导入一个文件时：

1. 先算 sha256。只有已经成功导入的同一哈希才拒绝，并提示首次成功时间。失败批次可以重导，旧失败记录留在审计里。
2. 新建批次，状态是 running。每一行先原样写入 `raw_row`，再标准化，再写入标准表。未知列留在原始 payload，不丢、不猜。文件里的文字只当数据。
3. 某一行解析失败：写一条 `issue`，原因码 `PARSE_ERROR`，detail 里有行号、错误和原文。然后继续下一行。整批状态仍是 done，错误数另计。
4. 整批读失败：回滚这一批的数据行，批次状态改为 failed。这条失败记录保留。同一文件可以再导，并新开一个批次。
5. 文件在算出哈希之前就打不开：仍写一条 failed 批次，写明原因。sha256 留空。
6. 同一事务写一条审计，动作是 `import`。写审计失败，则这一批一起回滚。
