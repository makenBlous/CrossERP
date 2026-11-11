# 后端分期任务卡（P0–P5）

> **适用范围：** 这是 08 v4 后端与 Agent 的执行任务入口。文档只描述目标设计与可执行验收，不宣称这些接口已经在当前仓库实现。当前代码的历史任务卡见本目录的 `T01–T56`；接口契约、风险等级和实体原名以 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md) 及其 [实体目录](../design/08/ontology-entities.yaml)、[OpenAPI 草案](../design/08/openapi-draft.yaml) 为准。

## 共用验收约定

- 每张卡都要在 SQLite 演示库和 MySQL 8.4 正式目标库执行迁移往返；PostgreSQL 只在明确启用时验证。
- 每个接口都要检查实体动作、`x-crosserp.permission`、`x-crosserp.riskTier`、审计结果和数据范围。金额统一使用 `Money.amountMinor` 万分位整数，禁止浮点。
- “同一动作三路径”指网页、主智能体/子智能体（带委托通行证）和导入投射；三者的成功结果、权限拒绝和审计字段必须一致。
- 演示口径采用 08 第 12.2 节的默认值，并标注“真实使用前需核实”；拍板后更新本卡和实现。
- 以下命令按仓库根目录执行。接口测试文件名是建议位置，落地时可按现有测试布局调整，但验收覆盖项不能减少。

## P0：底座（累计 41 个页面，88 个接口）

### P0-01 认证、会话与平台底座

- **目标：** 让前端通过统一会话、文件、任务、店铺和错误码接口接入真实后端。
- **范围：** OpenAPI `auth`、`platform`、`files`、`tasks`、`stores`、幂等与错误响应；路径前缀 `/auth`、`/files`、`/tasks`、`/stores`、`/health`。保留 `GET /auth/me` 为会话和有效权限唯一来源。
- **涉及实体：** `UserAccount`、`ApiToken`、`FileObject`、`Task`、`Store`、`IdempotencyKey`，见 [ontology-entities.yaml](../design/08/ontology-entities.yaml)。
- **权限与 AI 风险：** 登录、当前用户和文件元数据按登录人权限；读取为无（只读）/ `R`；上传、任务取消等改数据动作按实体目录的 `riskTier` 执行。Agent 继承登录人权限，不能扩权。
- **依赖：** 数据库会话、现有登录实现、OpenAPI 草案。
- **交付物：** `/api/v1` 路由、错误码表、幂等处理、`GET /auth/me` 集成测试。
- **验收标准：** `uv run pytest tests/web tests/integration -q`；未登录返回统一 401；重复幂等键不重复写入；权限矩阵覆盖登录人、停用账号和数据范围；网页与 mock 点击对同一接口的请求/响应一致；密钥扫描命令无命中。
- **要先拍板的事项：** 账号与店铺清单未定，演示默认使用单法人、内网服务器；真实使用前需核实。

### P0-02 权限引擎与旧 15 点映射

- **目标：** 先把旧后端 15 个权限点映射到前端 811 个 `doctype:action` 目录，消除权限漂移。
- **范围：** `iam` 模块的角色继承、用户例外、数据范围、字段策略、职责分离、临时授权和权限解释；路径前缀 `/admin/roles`、`/admin/permissions`、`/admin/permission-matrix`、`/admin/data-scopes`、`/admin/field-policies`。
- **涉及实体：** `Role`、`PermissionPoint`、`DataScope`、`FieldPolicy`、`TempGrant`、`AccessReview`、`SodRule`。
- **权限与 AI 风险：** 查询权限目录为无（只读）/ `R`；改角色、字段和数据范围为高/ `L2`，仅真人并按审批规则；Agent 不可调用高危权限动作。
- **依赖：** P0-01、前端 `permissionCatalog`、[OpenAPI 草案](../design/08/openapi-draft.yaml)。
- **交付物：** 15 点映射表、统一 `require(permission)`、数据范围过滤器、拒绝审计事件。
- **验收标准：** `uv run pytest tests/guard tests/web -k "permission or route" -q`；21 角色 × AI 开/关矩阵逐项返回预期 200/403；同一动作经网页、Agent 和导入投射的拒绝原因一致；mock 点击与接口契约一致；密钥扫描无命中。
- **要先拍板的事项：** 811 点的 manifest 源头仍待定，演示默认由模块 manifest 注册，真实使用前需核实。

### P0-03 审计、审批中心与实体动作执行器

- **目标：** 让所有实体动作走统一执行器、版本记录和审批解析，并保留哈希链审计。
- **范围：** `audit`、`approvals`、`ontology`、`action-dispatcher`；路径前缀 `/audit`、`/approvals`、`/workflow/rules/resolve`、`/ontology/entity-types`、`/entities/{type}/{id}/lineage`。
- **涉及实体：** `AuditLog`、`Approval`、`EntityType`、`EntityVersion`、`WorkflowRule`、`ActionExecution`。
- **权限与 AI 风险：** 查询审计、实体定义和审批状态为无（只读）/ `R`；审批决定和改账动作按 08 第 4.4、4.6 节，高风险最多起草/待审；配置了审批人就必须审，找不到可用审批人时人发起直接生效并留痕，AI 发起的钱账/高风险动作退回发起人确认。
- **依赖：** P0-01、P0-02、现有哈希链。
- **交付物：** 动作执行器、实体版本链、审批人解析、同事务审计中间件。
- **验收标准：** `uv run pytest tests/guard tests/integration -k "audit or approval or action" -q`；并发审批只成功一次；不能自批；审计哈希可离线校验；三路径结果与拒绝原因一致；密钥扫描无命中。
- **要先拍板的事项：** 审批人从流程配置解析已拍板；等待确认超时等具体时长是演示默认值，真实使用前需核实。

## P1：主数据、数据进入链路与快赢（累计 61 个页面，64 个接口）

### P1-01 商品主数据与映射

- **目标：** 先接入见效最快的 SKU、Listing、类目、品牌、组合装和平台映射页面。
- **范围：** `catalog`；路径前缀 `/catalog/skus`、`/catalog/costs`、`/catalog/listings`、`/catalog/categories`、`/catalog/brands`、`/catalog/mappings`、`/catalog/bundles`、`/catalog/lookups`。
- **涉及实体：** `Sku`、`SkuCost`、`Listing`、`Category`、`Brand`、`SkuMapping`、`Bundle`、`CatalogLookup`。
- **权限与 AI 风险：** 查询为 `R`；新增/修改非钱账主数据为中 / `M3`，可撤销并进每日站内摘要；删除使用作废动作，不能物理删除；AI 建议映射必须人确认。
- **依赖：** P0 全部、现有主数据服务。
- **交付物：** JSON 接口适配层、实体动作映射、字段权限和审计断言。
- **验收标准：** `uv run pytest tests/web tests/integration -k "catalog or sku or listing" -q`；金额字段以 `Money` 返回；权限矩阵与 mock 点击一致；网页/Agent/导入三路径的成功和 403 一致；密钥扫描无命中。
- **要先拍板的事项：** SKU 成本会计口径使用演示默认值，真实使用前需核实。

### P1-02 数据进入、清洗、去重与投射

- **目标：** 原件不可改，经过清洗校验、去重和实体对齐后，投射为预定义实体动作。
- **范围：** `ingest`；路径前缀 `/ingest/batches`、`/ingest/raw-records`、`/ingest/issues`、`/ingest/mapping-rules`、`/ingest/dedup-candidates`、`/entities/{type}/{id}/lineage`。
- **涉及实体：** `IngestBatch`、`FileObject`、`RawRecord`、`CleansingIssue`、`MappingRule`、`DedupCandidate`、`EntityVersion`。
- **权限与 AI 风险：** 原件和问题读取为 `R`；清洗处理、去重合并、投射为中 / `M3`，可撤销；Agent 先处理，处理不了转交上传这批数据的人；钱账只生成草稿。
- **依赖：** P0-03、现有 import batch/raw row 和连接器。
- **交付物：** 批次状态机、不可变原件、溯源查询、投射动作适配器。
- **验收标准：** `uv run pytest tests/integration tests/guard -k "ingest or import or lineage" -q`；同一文件重放不重复投射；坏行有原因码且原件保留；三路径拒绝一致；mock 点击验证与 OpenAPI 一致；密钥扫描无命中。
- **要先拍板的事项：** 外部平台账号与同步频率未定，P1 只验文件导入；真实使用前需核实。

### P1-03 结算对账快赢接口

- **目标：** 把已有确定性结算、对账、异常、利润、科目、汇率和导出服务包成 `/api/v1` JSON，避免重写核心计算。
- **范围：** `settlement`、`reconciliation`、`profit`、`issues`；路径前缀 `/finance/imports`、`/finance/settlements`、`/finance/reconciliations`、`/finance/issues`、`/finance/profit`、`/finance/accounts`、`/finance/fx`、`/finance/exports`。
- **涉及实体：** `Settlement`、`SettlementLine`、`Reconciliation`、`ReconciliationMatch`、`Issue`、`ProfitSnapshot`、`Account`、`FxRate`。
- **权限与 AI 风险：** 计算、匹配、差异分析和利润/凭证/余额查询为无（只读）/ `R`；处理差异为中 / `M3`；生成凭证、调账和写出为高或危，Agent 只能起草/待审或禁用。
- **依赖：** P1-02、现有 recon/profit/issues 服务。
- **交付物：** 24 个快赢接口、统一分页/错误格式、金额与来源行引用。
- **验收标准：** `uv run pytest tests/unit tests/integration tests/web -k "recon or profit or issue or settlement" -q`；golden 逐分一致；未匹配项 100% 有原因码；同一动作三路径一致；mock 点击和 OpenAPI 一致；密钥扫描无命中。
- **要先拍板的事项：** 会计科目、汇兑损益和期间使用演示默认值，真实使用前需核实。

## P2：业务主流程（累计 109 个页面，111 个接口）

### P2-01 订单、库存与物流

- **目标：** 打通订单、库存台账、收货、出库、头程和物流状态。
- **范围：** `sales`、`inventory`、`logistics`；路径前缀 `/sales/orders`、`/inventory`、`/inventory/movements`、`/logistics/shipments`、`/logistics/carriers`。
- **涉及实体：** `SalesOrder`、`SalesOrderLine`、`InventoryPosition`、`StockMovement`、`Warehouse`、`Shipment`、`Carrier`。
- **权限与 AI 风险：** 查询为 `R`；库存和物流草稿为中 / `M3`；过账、付款或改账动作按高 / `L2`，必须走审批；危动作仅真人。
- **依赖：** P1-01、P1-02、P0-03。
- **交付物：** 状态机接口、移动加权库存流水、数据范围过滤。
- **验收标准：** `uv run pytest tests/web tests/integration -k "order or inventory or logistics" -q`；并发状态转移幂等；金额无浮点；网页/Agent/导入三路径及审计一致；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 库存计价和物流时区采用演示默认值，真实使用前需核实。

### P2-02 补货、采购与站内通知

- **目标：** 打通“补货 → 采购 → 收货 → 头程 → 出库”，并提供站内待办。
- **范围：** `replenishment`、`procurement`、`notifications`、`workspace`；路径前缀 `/replenishment`、`/procurement`、`/notifications`、`/workspace`。
- **涉及实体：** `ReplenishmentPlan`、`PurchaseRequest`、`PurchaseOrder`、`GoodsReceipt`、`Notification`、`Task`。
- **权限与 AI 风险：** 计划试算和报表为低 / `L3`；采购、合同和收货草稿为中 / `M3`；付款和入账为高 / `L2`，审批规则不设金额上限。
- **依赖：** P2-01、P0-03。
- **交付物：** 计划版本、采购状态机、通知查询与已读动作。
- **验收标准：** `uv run pytest tests/web tests/integration -k "replenish or procurement or notification" -q`；状态机非法跳转返回统一错误；权限矩阵、审计和 mock 点击一致；同一动作三路径一致；密钥扫描无命中。
- **要先拍板的事项：** 补货阈值和采购审批模板使用演示默认值，真实使用前需核实。

## P3：财务、税务与数字孪生（累计 152 个页面，86 个接口）

### P3-01 资金、总账、核销与税务

- **目标：** 接入应收应付、核销、清分、总账、成本、税务、费用报销和预算查询/草稿流程。
- **范围：** `finance`、`ledger`、`tax`、`expense`、`budget`；路径前缀 `/finance/receivables`、`/finance/payables`、`/finance/writeoffs`、`/ledger`、`/tax`、`/expenses`、`/budgets`。
- **涉及实体：** `Receivable`、`Payable`、`Writeoff`、`Voucher`、`VoucherLine`、`TaxRule`、`ExpenseClaim`、`Budget`。
- **权限与 AI 风险：** 所有查询（含凭证、余额和薪资查询）为无（只读）/ `R`；生成凭证、调账、过账、付款、核销和导出写账最高为高 / `L2`，只能起草/待审；删除为危 / `N` 或 `H`。
- **依赖：** P1-03、P2-01、P0-03；唯一写出口 `ledger/write_service.py`。
- **交付物：** 财务 JSON 接口、借贷平衡校验、审批绑定、审计导出。
- **验收标准：** `uv run pytest tests/guard tests/integration tests/web -k "ledger or voucher or finance" -q`；未审批写出 403；借贷逐分平衡；同一动作三路径拒绝一致；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 科目编码、汇兑损益和税率均使用演示默认值，真实使用前需核实；外部账套先金蝶、再用友。

### P3-02 数字孪生与推演副本

- **目标：** 在副本上快照、试算和比较偏差，满意后只生成草稿走原审批链。
- **范围：** `twin`；路径前缀 `/twin/snapshots`、`/twin/scenarios`、`/twin/drifts`、`/twin/compare`。
- **涉及实体：** `TwinSnapshot`、`TwinScenario`、`TwinDrift`、`EntityVersion`。
- **权限与 AI 风险：** 快照、试算和归档为低 / `L3`；偏差处理和转交为中 / `M3`；转草稿按原动作重新检查权限和风险；推演不能直接改正式账。
- **依赖：** P2-01 的库存流水、P0-03、P3-01 的草稿接口。
- **交付物：** 副本隔离、偏差处理、转草稿接口和审计证据。
- **验收标准：** `uv run pytest tests/integration tests/web -k "twin or scenario or drift" -q`；正式库在推演期间无写入；转草稿重新走审批；三路径结果/拒绝一致；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 同步频率（库存每日、物流每 6 小时、银行每日）是演示默认值，真实使用前需核实。

## P4：智能体、知识库与平台/账套集成（累计 198 个页面，103 个接口）

### P4-01 智能体中心与委托通行证

- **目标：** 在独立 Agent worker 进程和独立 Python 环境中运行 DeerFlow SDK；主、子智能体继承登录人权限，通行证自动签发、续期和作废。
- **范围：** `agent`；路径前缀 `/agent/assistants`、`/agent/conversations`、`/agent/suggestions`、`/agent/tools`、`/agent/model-config`、`/agent/delegations`（仅管理员审计读取）。禁止 bash、沙箱和 Docker 代码执行。
- **涉及实体：** `Agent`、`AgentConversation`、`AgentSuggestion`、`RegisteredFunction`、`Delegation`、`ModelConfig`、`LlmCall`。
- **权限与 AI 风险：** 只读工具为 `R`；低/中风险按 `L3` 执行且中风险不限次数、可撤销、只进每日摘要；改账最高 `L2`；危动作 `N/H` 禁用。子智能体与主智能体相同执行权，但每步按被代表人当前权限回查。
- **依赖：** P0-02、P0-03、P3-01；DeerFlow 版本锁定仍未核实。
- **交付物：** worker、通行证中间件、OpenAI 兼容三项模型设置（`baseUrl`、`apiKey`、`model`）和密钥加密存储。
- **验收标准：** `uv run pytest tests/agent tests/guard tests/integration -q`；权限变化/登出/切换账号立即使旧通行证失效并在下次消息静默续签；子智能体不可扩权；关闭 AI 时所有工具停止；密钥扫描无命中；mock 点击与接口一致。
- **要先拍板的事项：** DeerFlow 正式版本和 worker 共用领域包方式未核实，演示默认使用已读源码验证的 SDK 嵌入方式，真实使用前需核实。

### P4-02 知识库与规则编译

- **目标：** 对业务知识、规则和实体页做权限隔离的整理、检索、体检和引用。
- **范围：** `knowledge`；路径前缀 `/kb/spaces`、`/kb/pages`、`/kb/compile-runs`、`/kb/search`、`/kb/entity-pages`。
- **涉及实体：** `KnowledgeSpace`、`KnowledgePage`、`KnowledgeCompileRun`、`KnowledgeReview`、`EntityType`。
- **权限与 AI 风险：** 读取继承来源空间和实体权限，为 `R`；知识页草稿为中 / `M3`；空间配置审核人就必须审核，未配置时按拍板规则直接生效并留痕；不跨空间泄露。
- **依赖：** P0-02、P4-01、P1-02 溯源。
- **交付物：** 权限过滤、引用到原件/实体、编译运行审计。
- **验收标准：** `uv run pytest tests/web tests/agent -k "knowledge or kb" -q`；无权限来源不可检索；网页与 Agent 返回同一过滤结果；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 向量检索实现与保留期未定，演示默认使用现有数据库查询，真实使用前需核实。

### P4-03 平台适配器与外部账套

- **目标：** 按文件导入 → Amazon → Shopify → 领星接入平台，并以金蝶、用友顺序提供外部账套适配器。
- **范围：** `connectors`、`channels`、`ledger_targets`；路径前缀 `/integrations`、`/connectors`、`/ledger/targets`。所有适配器通过 manifest/entry point 注册，设置页按 schema 生成表单。
- **涉及实体：** `Connector`、`ImportBatch`、`Settlement`、`LedgerTarget`、`ExportArtifact`、`ApprovalChannel`。
- **权限与 AI 风险：** 连接器配置和密钥读取仅管理员真人；导入投射为中 / `M3`；外部写账为高/危，只能经审批和 `ledger/write_service.py`；IM 审批延后到 P5。
- **依赖：** P1-02、P3-01、P4-01。
- **交付物：** 适配器接口、配置 schema、金蝶 xlsx、用友预留适配器和脱敏日志。
- **验收标准：** `uv run pytest tests/integration tests/guard tests/web -k "connector or ledger_target or export" -q`；没有审批不能导出；密钥不回显、不进日志；同一动作三路径一致；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 平台账号、API 资格和真实金蝶/用友模板未核实，演示只使用文件和当前 xlsx 模板。

## P5：人事、行政、CRM、广告与 IM 审批（累计 237 个页面，77 个接口）

### P5-01 人事与薪资

- **目标：** 接入员工档案、组织、合同、考勤、薪资、社保公积金和工资条。
- **范围：** `hr`、`payroll`；路径前缀 `/hr/employees`、`/hr/contracts`、`/hr/attendance`、`/payroll/runs`、`/payroll/slips`、`/payroll/rules`。
- **涉及实体：** `Employee`、`EmploymentContract`、`AttendanceRecord`、`PayrollRun`、`PayrollSlip`、`SocialSecurityRule`。
- **权限与 AI 风险：** 薪资查询按字段和本人范围为 `R`；薪资计算、发布和导出写账为高 / `L2`，必须审批；危权限仅真人。AI 可读到被代表人有权看的字段。
- **依赖：** P0 权限/审计、P3 财务写出口。
- **交付物：** 敏感字段策略、工资批次状态机、审计与导出控制。
- **验收标准：** `uv run pytest tests/web tests/guard -k "employee or payroll or salary" -q`；越权字段返回 403/脱敏；薪资发布无审批失败；三路径和 mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 薪资和个税口径为演示默认值，真实使用前需核实。

### P5-02 行政、CRM 与广告

- **目标：** 最后接入行政资产/费用、客户与线索、营销活动和广告数据。
- **范围：** `admin`、`crm`、`marketing`、`ads`；路径前缀 `/admin/assets`、`/admin/expenses`、`/crm`、`/marketing`、`/ads`。
- **涉及实体：** `Asset`、`AdministrativeRequest`、`Customer`、`Lead`、`Opportunity`、`AdCampaign`、`AdSpend`。
- **权限与 AI 风险：** 查询为 `R`；客户、线索和广告草稿为中 / `M3`，可撤销；付款、费用入账和删除动作按高/危；删除统一作废。
- **依赖：** P0 权限、P2 工作台/通知、P3 财务。
- **交付物：** P5 页面接口、数据范围、可插拔渠道接口。
- **验收标准：** `uv run pytest tests/web tests/integration -k "crm or marketing or ad or administrative" -q`；角色矩阵和字段策略通过；网页/Agent/导入三路径一致；mock 点击一致；密钥扫描无命中。
- **要先拍板的事项：** 客户字段、广告平台和费用科目未定，演示默认值仅用于样例，真实使用前需核实。

### P5-03 IM 审批与全量回归

- **目标：** 在平台内审批稳定后，以可插拔渠道接入 IM 卡片审批，并完成 237 个页面的全量回归。
- **范围：** `channels` 的 `ApprovalChannel`；路径前缀 `/im/bindings`、`/im/approvals`、`/im/settings`、`/approvals`。IM 只产出决定命令，最终仍调用平台内 `approvals.decide`。
- **涉及实体：** `ApprovalChannel`、`ImBinding`、`Approval`、`DecisionCommand`、`SecurityEvent`。
- **权限与 AI 风险：** 绑定和渠道配置为高/危，仅真人；审批卡片读取为 `R`；AI 不绕过平台内审批，不直接调用外部写账。
- **依赖：** P0–P5 其他卡、平台内审批、渠道适配器。
- **交付物：** 首个 IM 适配器、回调校验、幂等决定命令、全量回归证据。
- **验收标准：** `uv run pytest tests/web tests/guard tests/integration -k "approval or im or security" -q`；重复回调只处理一次；权限矩阵和审计链通过；三路径与 mock 点击一致；密钥扫描无命中；记录累计页面数 237。
- **要先拍板的事项：** 首个 IM 渠道（飞书或企业微信）未定；演示默认只验平台内审批，真实使用前需核实。
