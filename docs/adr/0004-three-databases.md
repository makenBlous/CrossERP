# ADR 0004: 三库兼容

- 状态：已采用
- 相关任务：T04、T05、T16、T30、T52

## 背景

个人用户需要零配置 SQLite，团队可能已有 PostgreSQL 或 MySQL 运维。

## 决定

业务模型只用 SQLAlchemy 通用类型和项目方言类型：SQLite 默认，PostgreSQL 18 和 MySQL 8.4 在 CI 和 Compose 中验证。金额使用 `Money4`，时间使用 `UtcDateTime`；长文本使用 `Text`，MySQL 使用 `MEDIUMTEXT` variant。

## 后果

迁移必须在三库往返，不能依赖 PG 专属类型。数据库差异集中在类型和 `db/dialects.py`，部署文档说明连接串和授权差异。
