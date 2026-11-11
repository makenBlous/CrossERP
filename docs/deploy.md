# 部署

本文状态：**目标部署设计；当前代码可直接运行的部分已实现**。

## 目标

- 内网服务器、单法人、单套账，不做多租户。
- 正式数据库为 MySQL 8.4 LTS；本机演示可用 SQLite。
- FastAPI 应用进程与独立 agent worker 进程分开；worker 使用独立 Python 环境并以 DeerFlow SDK 运行。
- 不安装 Docker 也可运行。仓库虽有 `docker-compose.yml`，它只作为可选的开发/数据库辅助，不是生产必需。
- 不单独部署 DeerFlow 服务，不开放 DeerFlow 专用端口；浏览器只访问 CrossERP。

## 已实现现状

当前 `src/crosserp/web/app.py` 提供 HTML 页面和 `/health`，CLI、导入、对账、利润、审批、凭证、审计、认证和 agent 只读工具已在代码中。独立 worker、实体动作执行器和 `/api/v1` JSON 层仍是 [08](design/08-后端模块与API设计.md) 的仅设计目标。

## 运维纪律

使用环境变量 `CROSSERP_DATABASE_URL`，密钥只放部署环境；迁移由 Alembic 执行；审计表只追加；关闭 AI 后人工流程必须可用。MySQL 自检和 worker 生命周期以 [ADR 0008](adr/0008-deerflow-embedded-worker.md) 与 [08 第 10、11 章](design/08-后端模块与API设计.md) 为准。
