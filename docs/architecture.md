# 架构

本文状态：**已实现现状 + 仅设计目标**。

## 已实现

`src/crosserp/` 是 Python 模块化单体：FastAPI + Jinja2/HTMX、SQLAlchemy、Alembic、Pydantic 和 Typer。现有模块包括 `core`、`db`、`connectors`、`recon`、`profit`、`issues`、`approval`、`vouchers`、`ledger`、`audit`、`auth`、`agent`、`mcp_server`、`observability`、`evals` 和 `web`。数据库 schema 由 19 个迁移管理；网页当前是 HTML 路由，尚无 `/api/v1` JSON 层。

导入链路按表头读取，原始行留存并带 provenance；对账、利润和金额由确定性代码计算；`ledger/write_service.py` 是唯一写账/导出出口；审计和安全事件使用追加哈希链。

## 目标设计（仅设计）

后端仍是单体。网页、CLI、导入、agent、MCP 和定时任务都投射到实体动作执行器；实体目录、接口和风险以 [08](design/08-后端模块与API设计.md) 及其附件为准。DeerFlow 以独立 Python 环境的 SDK worker 嵌入，不单独部署服务。

## 运行边界

正式环境目标为内网单法人 MySQL 8.4，不做多租户；本机演示保留 SQLite，PostgreSQL 仅作备选。Docker Compose 文件存在，但仅为可选开发/数据库辅助方式；生产可不装 Docker。详见 [部署](deploy.md)、[数据库](database.md) 和 [08 第 10、11 章](design/08-后端模块与API设计.md)。
