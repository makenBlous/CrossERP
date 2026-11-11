# 数据库

本文状态：**已实现现状 + 仅设计目标**。

## 现状

代码使用 SQLAlchemy 通用类型和 Alembic 迁移。默认连接为 SQLite；MySQL 8.4 与 PostgreSQL 18 保留兼容路径。金额使用 `Money4`，SQLite 存万分位整数，其他数据库使用 `DECIMAL(19,4)`；汇率用 `FxRate`，时间用 `UtcDateTime`。当前 schema 和迁移以 `src/crosserp/db/` 为准。

## 目标环境

正式环境以 MySQL 8.4 LTS 为主；SQLite 供本机演示，PostgreSQL 仅在 [08 第 11.3 节](design/08-后端模块与API设计.md) 的条件满足时使用。不要把三库兼容写成部署目标。

## 约束

- 业务代码不写原生 SQL；方言差异集中在 `db/dialects.py`。
- 金额禁止浮点，超过 4 位小数直接报错；统一 `CROSSERP_DATABASE_URL`。
- 迁移只追加，必须验证 `upgrade head → downgrade base → upgrade head`。
- `audit_log` 和安全事件链只追加，不更新、不删除。

实体和目标表以 [`ontology-entities.yaml`](design/08/ontology-entities.yaml) 为设计目录；未列入当前迁移的表均为仅设计。
