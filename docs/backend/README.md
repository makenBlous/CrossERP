# 后端开发指南

本文状态：**已实现与仅设计分开记录**。只读代码核实范围为 `src/crosserp/`；目标模块以 [08 后端模块与 API 设计](../design/08-后端模块与API设计.md) 为准。

## 1. 当前代码包（已实现）

- `core/`：金额、枚举、模型和错误；金额走 `Money`/`Decimal`。
- `db/`：SQLAlchemy schema、通用类型、session、repo 和 19 个 Alembic 迁移。
- `connectors/`：Amazon Settlement V2、Shopify Payouts、通用 YAML 映射及导入。
- `recon/`、`profit/`、`issues/`：对账、利润和异常。
- `approval/`、`vouchers/`、`ledger/`：审批状态机、凭证和唯一写账出口。
- `audit/`：业务审计与安全事件哈希链，追加写。
- `auth/`：密码、会话、Token、角色和权限。
- `agent/`、`mcp_server/`、`observability/`、`evals/`：只读 agent 工具、MCP、LLM 监控和评测。
- `web/`、`cli.py`：现有 Jinja/HTMX 网页和 CLI。当前没有 `/api/v1` JSON 路由；这是 08 的目标设计。

## 2. 目标包结构（仅设计）

08 规划 25 个领域模块。实体、属性、关系、状态机和动作只看 [`08/ontology-entities.yaml`](../design/08/ontology-entities.yaml)；接口只看 [`08/openapi-draft.yaml`](../design/08/openapi-draft.yaml)。新增模块应先登记实体动作，再由 API、网页、agent、导入和定时任务投射到同一执行器。

## 3. 写路径、实体和动作

所有会改账或导出凭证的操作必须进入 `ledger/write_service.py`（[ADR 0001](../adr/0001-single-write-path.md)）。业务代码不得直接导入 `ledger.targets`。动作执行器必须依次执行：身份与数据范围 → 权限点 → 风险级别 → 职责分离 → 幂等与版本 → 业务动作 → 审计；推演只在副本上运行，满意后才生成草稿。

## 4. 权限、风险和审批

agent 继承登录人的权限，只能收窄，不能扩权；网页按钮、CLI、MCP、导入和 worker 走同一套检查。风险名称和标注以 08 第 4.4 节及附件的 `riskTier` 为准：无（只读，`L1`/`R`）、低（`L3`）、中（`L3`/`M3`）、高（`L2`）、危（`L0`/`N`/`H`）。只读和低/中风险可按权限执行；改账动作最多到起草/待审；权限与治理高危写操作禁止 agent 执行。

提交单据时由流程配置解析审批人。配置到可用审批人就必须审批，提交人和被代表人不能自批；没有配置或解析不到账号时，人发起的单据直接生效并留痕；AI 发起的高风险或钱账动作退回发起人本人确认后才生效。审批不设金额上限。

## 5. 接口约定

所有 POST 使用 `Idempotency-Key`；同键同请求体返回首次结果，同键不同请求体返回 `409 IDEMPOTENCY_CONFLICT`。带版本的资源使用 `expectedVersion`，冲突返回 `409 CONFLICT_VERSION`。统一错误至少包括 `VALIDATION_ERROR`、`FORBIDDEN`、`NOT_FOUND`、`CONFLICT_VERSION`、`IDEMPOTENCY_CONFLICT`、`APPROVAL_REQUIRED`、`RISK_BLOCKED` 和 `INTERNAL_ERROR`。

金额结构为 `Money = {amountMinor: int64, currency}`，`amountMinor` 是万分位整数（`SCALE=10000`），中间计算不用浮点；汇率和高精度单价用十进制字符串。

## 6. 数据库与迁移

正式环境目标为 MySQL 8.4 LTS；本机演示保留 SQLite，PostgreSQL 为备选。MySQL 需要 `utf8mb4`、`STRICT_TRANS_TABLES`，并使用 `?charset=utf8mb4`；详细条件见 [08 第 11 章](../design/08-后端模块与API设计.md)。每个迁移都要能 `upgrade head → downgrade base → upgrade head`；使用通用 SQLAlchemy 类型，禁止 PG 专属类型。迁移只追加，审计表不更新、不删除。

## 7. agent worker

DeerFlow 以 SDK 嵌入独立 agent worker 进程和独立 Python 环境运行，不部署 DeerFlow 服务；CrossERP API 进程通过任务/事件表通信。通行证由系统自动签发、静默续期并在登出、切换账号、权限变化、停用或关闭 AI 时作废，用户无感。详见 [ADR 0008](../adr/0008-deerflow-embedded-worker.md) 和 [08 第 10 章](../design/08-后端模块与API设计.md)。AI 不执行代码：不开 bash、沙箱和 Docker，只调用注册函数或 MCP 工具。

## 8. P0 公共底座迁移与路由约定

P0 公共底座使用迁移 `0020_idempotency_key`，为 API 的 `Idempotency-Key` 提供 24 小时重放记录。后续并行块从 `0020` 派生：platform=`0021`、iam=`0022`、audit-approval=`0023`、ontology=`0024`；各迁移的 `down_revision` 先写 `0020`，合并时由合并任务串成线性历史。

JSON 路由放在 `src/crosserp/api/routers/<module>.py` 并暴露名为 `router` 的 FastAPI 路由器。`crosserp.api` 会自动发现并以 `/api/v1` 前缀注册；端点用 `api_endpoint` 声明 `entity`、`action`、`permission` 和 `risk_tier`，同时生成 OpenAPI 的 `x-crosserp`。业务代码通过 `get_principal`、`PermissionService.require` 做身份和权限检查，用 `AuditRecorder.record` 在同一事务追加审计，并把改写动作交给 `ActionDispatcher` 按固定阶段执行。

## 9. 分期验收

P0–P5、累计页面和每期验收以 [08 第 8 节](../design/08-后端模块与API设计.md) 为准；任务卡见 [`docs/tasks/backend-phases.md`](../tasks/backend-phases.md)（由其他组维护，若尚不存在视为预定文件）。每期都要证明人工路径可用、权限与审计可追溯、金额逐分一致。
