# 08 后端功能模块与 API 接口设计
> **仓库内位置与附件链接**：本文是后端与 agent 的唯一设计依据（仅设计，代码尚未完整实现）。配套附件位于 [08/ontology-entities.yaml](08/ontology-entities.yaml)、[08/openapi-draft.yaml](08/openapi-draft.yaml) 和 [08/page-api-coverage.csv](08/page-api-coverage.csv)。正文中的附件引用均指向这些仓库相对路径；生成脚本与中间数据位于 box /workspace/crosserp-backend-design/work/，**不在仓库**。


- 文档日期：2026-11-11（Asia/Shanghai）；**v4**（按 maken 第二次回复修订：风险分级只看是否改数据、通行证全自动用户无感、审批人从流程配置解析、OpenAI 兼容模型前端填写、禁止 AI 执行代码、可插拔渠道与适配器；agent 独立 worker；修订内容见第 12.3 节与第 14 章）
- 依据：仓库 `main=49101ad`（本地未推送，含 07 财务库存页）只读快照；`docs/design/00–07`；`docs/adr/0001–0004`；前端 `src/config/pages.ts`、`src/config/permissions.ts`、`src/api/*.ts`（含每个函数上方的「未来: METHOD /api/v1/...」注释）、`src/types/*.ts`、`src/mocks/*`。v2 另外依据：`bytedance/deer-flow` commit `2a97ec3`、`nashsu/llm_wiki` commit `e08cfce` 的源码与文档（只读克隆），Palantir Foundry Ontology 官方文档，Digital Twin Consortium 定义与术语表，ISO/IEC 30173 摘要；v3 另外依据 MySQL 8.4 官方手册与 Oracle 生命周期公告；v4 另外依据 DeerFlow 的模型配置（`config.example.yaml`、managed models）与沙箱/工具源码。
- 配套产物（同目录）：
  - [`08/ontology-entities.yaml`](08/ontology-entities.yaml)（v2 新增）：实体目录，包括实体类型、属性、关系、状态机、动作 → 权限点 → 接口、事件、孪生同步规则；
  - [`08/openapi-draft.yaml`](08/openapi-draft.yaml)（OpenAPI 3.1，0.4.0-draft；Redocly CLI 与 swagger-parser 两个工具校验通过）：每个操作的 `x-crosserp` 都标注了实体和动作；
  - [`08/page-api-coverage.csv`](08/page-api-coverage.csv)：页面 → 接口 → 涉及实体 → 实体动作 → 权限点。
- 范围：只做设计。没有改代码、没有提交、没有推送。
- 标注约定：「推断」= 有依据但需实现时确认；「未核实」= 没找到证据；「演示默认值，真实使用前需核实」= 会计/税务/人事口径。

---

## 0. 一页结论

1. **后端不用推倒重来。** 仓库已有一个能跑的 Python 后端：FastAPI + SQLAlchemy 2 + Alembic + Pydantic，支持 SQLite/PostgreSQL/MySQL，共 35 张表、19 个迁移、88 个测试文件。它已经做好的部分：导入、对账、利润、凭证、审批、哈希链审计、登录会话、API Token、LLM 监控，以及 9 个只读智能体工具和 MCP 服务。缺的是：一层给 Vue 前端用的 JSON `/api/v1` 接口（现在的 32 个路由都是 Jinja 网页），以及前端已经画出来的大部分业务模块。
2. **设计规模：25 个领域模块、529 个接口（441 个路径），对应 166 个实体类型、500 个实体动作。** 前端 238 个页面 ID 中，除 2 个纯说明页外，236 个都至少对应一个接口，**覆盖率 100%，没有未覆盖页**。前端 382 个 service 函数中，371 个已对上接口。另外 11 个是故意不实现的：演示用的角色可见性覆盖、通用占位出口和工具函数，见第 6 节。
3. **v2 以实体为核心（第 9 章）。**
   - 订单、SKU、库存、结算、凭证、员工等业务对象都登记在实体目录里，每个实体定义了属性、关系、状态机和允许的动作；每个动作对应一个权限点。
   - 529 个接口都是「某个实体的某个动作」的投影，网页、agent 工具、IM、定时任务、导入投射走同一个动作执行器。
   - 所有外部数据先原样落地，再经过清洗、校验、去重，投射成实体，并记录版本和来源。
   - 门店、SKU、库存、在途、资金、员工有数字孪生：定期同步、偏差核对、历史快照；补货和利润推演只在副本上算，不写真账。
4. **agent 用登录人的权限办事（第 10 章）。**
   - **DeerFlow 2.0 以 SDK 形式嵌入，不单独部署**（第 10.0 节）。v4：agent 跑在**独立的 worker 进程、独立的 Python 环境**里（第 10.1 节）。CrossERP 只写 5 个进程内工具，每次调用都在 CrossERP 重新判定权限。
   - **通行证全自动、用户无感**：系统自动签发、静默续期；登出、切换账号、权限变化、停用、关闭 AI 时自动立即作废。没有「我的通行证」页面，也没有任何要用户操作的步骤（第 10.5 节）。子智能体自动继承同一身份。
   - **主智能体和子智能体都有执行权，只按「改不改数据」分级**：只读全部可用；低、中风险自动执行（可撤销，不设次数限额）；改账等高风险最多到起草、待审；权限与治理的写操作禁用。
   - **模型兼容 OpenAI 接口**，在前端「模型设置」页填 `baseUrl`、`apiKey`、`model`；密钥加密存储、不回显、不进日志（第 10.8 节）。**AI 不能执行代码**：不开 bash、不开沙箱、不装 Docker（第 10.9 节）。
5. **接口契约以前端为准。** 前端函数注释里已经声明了 278 个不重复的未来接口。本设计原样采纳了其中 251 个，调整了 27 个，原因见第 6 节，主要是合并重复接口和统一审批决定入口。权限点全部使用前端权限目录（811 个 `doctype:action`）中已有的键；只建议新增 1 个：`landed_cost_voucher:create`。
6. **AI 怎么用（v4：只看动作改不改数据）：**
   - 258 个只读接口 AI 直接用（v3 为 224 个），**包括对账结果、利润、凭证、余额、报表、薪资等钱和账的查询**；能读到什么取决于被代表人自己的权限。
   - 37 个低风险 + 74 个中风险接口 AI 直接执行（L3）。对账的计算、匹配、差异分析属于这一类；中风险可撤销，**不设次数限额**，通知只进每日一条站内摘要。
   - 56 个高风险接口 AI 可以发起，结果是草稿或待审项（L2）。只有**改账**（生成凭证、调账、过账、付款、核销等）才受「最多到起草、待审」限制。
   - 104 个接口 AI 不能调用或只能由真人操作（v3 为 142 个），包括审批决定、权限与治理的写操作、密钥与模型设置、薪资计算与发布、导出写账。
   - **审批规则**（第 4.6 节）：配置了审批人就必须审，法人或老大也一样，不能自批；没配置或找不到可用账号就直接生效，并记「无审批人，直接生效」；AI 发起的高风险或钱账动作找不到审批人时，退回发起它的本人确认。
7. **建议分 6 期接入，前端可以逐模块从假数据切到真实接口：**
   - P0 底座：认证、权限、审计、审批中心、实体目录与动作执行器。
   - P1 主数据、数据进入链路，加上已有服务的结算对账（快速见效）。
   - P2 业务主流程。
   - P3 财务、数字孪生与推演。
   - P4 智能体、知识库和集成（平台接入顺序：文件导入 → Amazon → Shopify → 领星）。
   - P5 人事、行政、CRM、广告，以及 IM 审批（后期）。

   每期结束时能用真实数据跑通的页面数（累计）依次是：41 → 61 → 109 → 152 → 198 → 237（v3 把 IM 审批移到最后一期，所以中间几期略少；口径见第 13 章）。
8. **运行环境（maken 已定）**：沿用 Python 后端；正式环境 MySQL 8.4 LTS 为主（第 11 章）；内网服务器、一个法人、不做多租户；外部账套先金蝶、再用友；审批先在平台内，不设金额上限，职责分离保留；IM、邮件等以后通过可插拔渠道接入（第 4.11 节）。

---

## 1. 现状盘点

### 1.1 已有后端（`src/crosserp/`，181 个文件）

| 项 | 现状（实查） |
|---|---|
| 语言/框架 | Python ≥ 3.12；FastAPI ≥ 0.162；Uvicorn；Jinja2 + htmx 网页；Typer 命令行（`pyproject.toml`） |
| ORM/迁移 | SQLAlchemy ≥ 2.1；Alembic，19 个迁移（`0001_initial` … `0019_llm_text_columns`） |
| 数据库 | 默认 SQLite；可选 PostgreSQL（psycopg）与 MySQL（pymysql）。ADR 0004 要求三库兼容，金额列为 `Money4`（Decimal 四位小数；SQLite 存万分位整数） |
| 表（35 张） | `import_batch raw_row store sku sku_cost fee_reference fx_rate order_line settlement settlement_line fee recon_run match issue profit_snapshot audit_log audit_head approval voucher voucher_line prompt_version llm_call llm_tool_call llm_budget llm_alert eval_run export_artifact audit_checkpoint audit_export app_user user_role user_session api_token app_setting security_event` |
| 路由 | `web/app.py` 中 32 个页面/表单路由（`/login /logout / /imports /profit /profit/submit /approvals[/{id}[/decide]] /vouchers[/{id}[/download]] /ask /rows/{table}/{id} /account/tokens /llm[/calls/{id}] /audit[/verify|/export] /issues[/{id}] /security-log /settings /admin/users` 等）。**没有 `/api/v1` JSON 接口**（02 文档第 11 节同样结论） |
| 权限 | 固定 5 角色（admin/finance/operator/viewer/auditor）× 15 个权限点（`report.read`、`approval.decide`…），写在 `auth/permissions.py` 代码里，不是权限表 |
| 审批 | `approval/state.py` 状态机：draft→pending→approved/rejected，approved→exported，rejected→draft；有乐观锁（`ConcurrentModification`）和内容哈希（`approval/payload.py`） |
| 审计 | `audit/` 业务审计与安全事件两条只追加哈希链，支持检查点、导出包、离线校验（ADR 0003） |
| 写账 | `ledger/write_service.py` 是唯一写账/导出出口，检查批准状态、对象哈希、一次性令牌（ADR 0001）；目标：通用 Excel、金蝶 Excel |
| 连接器 | entry-point 插件：Amazon 结算 V2、Shopify 打款、通用列映射（领星/赛狐/模板映射 yaml） |
| 智能体 | `agent/tools.py` 9 个只读工具（利润、异常、订单、结算、对账汇总、审批状态、凭证、利润对比、规则检索）；`mcp_server` 用同一白名单；ADR 0002：LLM 不计算金额 |
| LLM 监控 | `llm_call`、`llm_tool_call`、预算、告警、评测、提示词版本 |
| 科目 | `config/accounts.example.yaml`，编码全部为「待会计核实」，加载器拒绝占位编码过账 |

### 1.2 前端（Vue3 + TS + Vuetify3 + Vite，Vuexy 底座）

| 项 | 量级（脚本统计） |
|---|---|
| 页面目录 `pageCatalog` | 238 个页面 ID，20 个菜单分组；`implemented=true` 151 个；阶段 now 97 / v1 59 / later 82；页面文件 244 个（缺 A04 忘记密码、A05 重置密码两页文件） |
| 权限点目录 | 811 个权限点，68 个单据类型（ERPNext 风格 `doctype:action`，含字段级如 `sku.cost:read`、`employee.salary:read`），每点带数据范围规则类型（all/store/department/self/owner/warehouse/amount） |
| 角色 | 16 个预置模板（owner_manager … external_viewer，可继承）+ 5 个旧角色兼容 = 21 个演示角色 |
| service 层 | `src/api/` 27 个文件、382 个导出函数；其中 288 个有「未来: METHOD /api/v1/...」注释（278 个不重复接口）；每个函数用 `assertPermission('doctype:action')` 做服务层权限校验 |
| 假数据 | `stores/mockdb.ts` + `mocks/seed`，`MockDatabase` 79 个集合；`types/` 309 个类型声明 |
| 金额 | `utils/money.ts` 的 `Minor` = 万分位整数（SCALE 10000），与后端 `Money4` 一致；但 HR 类型仍有 `*Cents`（如 `salaryCents`），`domain.ts` 部分为 `amount: number` —— **需统一**（见第 4.9 节） |
| 已在前端落地的安全约定 | 聊天发送时快照发起人（userId+role），返回时复核；登出/切换账号作废进行中的请求；登出整页刷新 |

### 1.3 主要差距

1. 前端权限键（`sales_order:read`）与后端旧权限键（`report.read`）是两套，需要一张映射表并以前端目录为准（旧键保留兼容）。
2. 后端只有固定角色，前端已按「权限表 + 可自建角色 + 继承 + 用户例外 + 数据范围 + 字段权限 + 职责分离」设计（02 第 13 节）。
3. 前端约 21 个业务域只有假数据：商品、库存、采购、物流、CRM、人事、知识库、智能体管理等，后端没有表。
4. 前端声明的接口中有 27 个与后端统一原则冲突，主要是重复的收件箱和分散的审批决定入口，第 6 节逐条给出处理。

---

## 2. 技术栈与总体架构

### 2.1 结论：沿用现有栈，不建议更换

- **沿用 Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Pydantic 2。** 理由如下：
  - 已有对账、利润、凭证、审批、哈希链审计、写账出口、连接器、智能体工具，并有 88 个测试文件，换栈等于重写最难的部分。
  - FastAPI 自动生成 OpenAPI，可直接给前端生成类型。
  - 智能体侧（pydantic-ai、MCP、DeerFlow 2.0）同属 Python 生态。
- **没有发现硬伤。** 下面两点要注意，但都不需要换栈：
  - 单进程同步请求不适合长任务，所以加一张数据库任务表和后台 worker（02 第 7 节已定）。
  - 正式环境以 MySQL 为主（maken 已定），兼容性要点见第 11 章。
- **数据库建议**：
  - 正式环境：**MySQL 8.4 LTS**（maken 已定；8.0 已于 2026-04 结束支持）。
  - 本机演示/单人：保留 SQLite。
  - PostgreSQL：只在第 11.3 节列出的条件出现时才换。
- **形态**：模块化单体，一个进程、一套库（02 第 1 节）。各业务域做成插件模块，有 manifest、权限点、菜单和事件，可以单独开关。

### 2.2 分层

```text
Vue 前端 ── /api/v1 JSON（新）──┐
Jinja 旧页面（过渡期保留）──────┤
agent worker（DeerFlow SDK）┼── FastAPI 进程 + worker 进程
IM 回调 / 定时任务 / 命令行 ─────┘
   ├─ api/<module>/router.py      路由：只做鉴权、参数、序列化，然后调用动作执行器
   ├─ ontology：实体目录 + ActionDispatcher（统一做身份→权限→数据范围→状态机→职责分离→agent 上限→业务校验→版本/日志/事件）
   ├─ <module>/services.py        业务规则（确定性计算，Decimal），以实体动作的形式注册
   ├─ ingest：落地 → 清洗 → 去重 → 投射成实体 → 溯源（所有外部数据的唯一入口）
   ├─ twin：孪生同步、偏差核对、快照、推演副本（推演只写副本库）
   ├─ agent_runtime：委托通行证 + DeerFlow SDK（DeerFlowClient）+ 5 个进程内工具 + 守卫中间件
   ├─ platform：权限引擎、审计、幂等、文件、任务、事件总线、模块开关
   ├─ workflow：统一审批中心（由现有 approval 升级）
   └─ ledger：唯一写账/导出出口（不拆、不绕开）
```

建议的包结构（推断，沿用现有包名，不改名）：`src/crosserp/api/`（新，按模块分 router）、`platform/`（新）、`catalog/ sales/ inventory/ procurement/ logistics/ accounting/ tax/ expense/ ads/ crm/ hr/ office/ knowledge/ notify/ integrations/ agent_control/ ontology/ ingest/ twin/ agent_runtime/`（新），现有 `recon/ profit/ issues/ vouchers/ connectors/ ledger/ approval/ audit/ auth/ agent/ observability/` 保留，注册进对应域。

---

## 3. 领域模块划分（25 个）

模块以实际页面为准；依赖箭头只能「下游用上游」，禁止反向（02 第 2 节）。v2 新增第 23–25 号模块。各模块的实体、属性、关系和动作以 [`08/ontology-entities.yaml`](08/ontology-entities.yaml) 为准，下表「核心实体」列保留表名写法。

| # | 模块（代码） | 职责 | 核心实体 | 主要依赖 | 发出事件（摘） | 页面 |
|---|---|---|---|---|---|---|
| 1 | 平台底座 `platform` | 登录会话、当前用户、文件、后台任务、店铺、单据关联与业务链追溯、幂等、模块开关 | app_user, user_session, api_token, file_object, job, store, document_link, idempotency_key | core, db | `identity.user.created` | A01–A06, SYS05, SYS11–13, ME01, D05 |
| 2 | 系统与权限 `iam` | 权限点目录、角色（可建/继承）、用户例外、数据范围、字段权限、临时授权、复核、职责分离、有效权限计算 | permission, role, role_permission, role_inherit, user_role, user_permission_override, data_scope, field_policy, temp_grant, access_review, sod_rule | platform | `permission.changed` | SYS01–04, SYS07–10, SYS14–18, SYS21–24 |
| 3 | 操作日志与审计 `audit` | 统一操作日志（人/AI/系统）、安全日志、哈希链校验、审计包、敏感告警、保留归档、AI 建议追溯 | audit_log（追加列）, security_event, audit_checkpoint, audit_export, audit_alert | platform | `audit.sensitive_action` | U01–U08, K09, SYS24 |
| 4 | 工作台与报表 `dash` | 首页聚合、待办、店铺对比、经营日历、报表目录与运行 | report_def, report_run | 各模块只读查询 | — | D01–D04, RP01–RP03 |
| 5 | 商品与主数据 `catalog` | SKU、成本期间、Listing、类目、品牌、平台 SKU 映射、组合装 | sku, sku_cost, listing, category, brand, sku_mapping, bundle | platform | `catalog.cost.changed` | P01–P09 |
| 6 | 订单与售后 `sales` | 订单、发货、退货登记与处置、异常订单、多渠道、履约 | sales_order, sales_order_line, sales_return, sales_fulfillment | catalog, inventory | `sales.order.shipped` `sales.return.received` | O01–O06 |
| 7 | 库存与补货 `inv` | 仓库、库存余额、流水、入出库/调拨/盘点、批次效期、预警、库存台账（移动加权）、补货计划与需求因子 | warehouse, stock_balance, stock_movement, stock_doc(+line), batch, stock_ledger_entry, replenishment_plan(+line), demand_factor | catalog, procurement | `inventory.moved` `inventory.below_safety` `inventory.batch.near_expiry` | I01–I17, I19–I20 |
| 8 | 采购与供应商 `proc` | 供应商、询价比价、合同、采购单、收货、采购退货、供应商对账、评估 | supplier, rfq, supplier_quotation, purchase_contract, purchase_order(+line), purchase_receipt(+line), purchase_return(+line), supplier_statement, supplier_score | catalog, inventory | `procurement.receipt.confirmed` `procurement.return.confirmed` | S01–S13 |
| 9 | 物流与头程 `logi` | 头程运单、发运/到仓、头程费用、物流商、运费模板、轨迹、费用核对 | shipment(+line,+charge), carrier, rate_card, tracking_event, freight_check | inventory | `logistics.shipment.arrived` `logistics.charge.recorded` | L01–L06 |
| 10 | 平台结算、对账与资金 `fin` | 文件导入、结算、对账、异常、利润、科目、汇率、费用映射、列映射、应收应付、核销、资金流水、导出产物 | import_batch, raw_row, settlement(+line), fee, recon_run, match, issue, profit_snapshot, fx_rate, fee_reference, ar_item, ap_invoice, clearing, cash_entry, export_artifact | catalog, sales, connectors | `import.batch.finished` `recon.run.finished` `issue.updated` | F01–F22, F39 |
| 11 | 总账与成本核算 `gl` | 凭证（生成/提交/冲销/导出）、总账、科目余额、三张报表、期末结账与反结账、成本结转、汇兑重估、到岸成本分摊、暂估应付、期初启用、库存与总账核对 | voucher(+line), voucher_rule, accounting_period, period_reopen_request, cogs_run, fx_revaluation, landed_cost_voucher(+line), grni_entry, opening_batch | fin, inv, proc, logi, workflow, ledger | `voucher.submitted` `accounting.cogs.drafted` `accounting.period.closing` `ledger.exported` | F12–F13, F23–F29, F32, F35–F38, F41, I17 |
| 12 | 税务 `tax` | VAT 申报跟踪（平台代缴只记录）、出口退税/免税资料与齐套校验 | vat_return, export_rebate_case, rebate_document | fin, sales, proc | `tax.rebate.validated` | F33–F34 |
| 13 | 费用报销与预算 `exp` | 报销、借款、差旅、费用标准、预算编制/占用/调整 | expense_claim(+line), employee_advance, travel_request, expense_policy, budget(+line), budget_adjustment | workflow, gl | `expense.claim.approved` `budget.threshold` | EX01–EX07, F30–F31 |
| 14 | 广告 `ads` | 广告活动、花费导入、效果、费用分摊（管理利润） | ads_campaign, ads_spend_import, ads_allocation | catalog, fin | `ads.allocation.changed` | AD01–AD04 |
| 15 | CRM 与客服 `crm` | 客户、线索、商机、联系人、跟进、工单、评价、赢单转订单 | crm_account, crm_lead, crm_opportunity, crm_contact, crm_activity, crm_ticket, crm_review | sales | `crm.opportunity.won` `crm.ticket.created/resolved` | R01–R14 |
| 16 | 审批中心 `wf` | 审批类型注册、多级规则与额度、抄送、代理、唯一决定入口、撤回 | approval（扩展）, approval_step, approval_rule, approval_type | iam | `workflow.item.created/decided` `approval.decided` | W01–W07 |
| 17 | 通知与 IM 插件 `notify` | 站内消息、订阅、通知规则、渠道插件（飞书/企微/钉钉/邮件/Webhook）、IM 身份绑定、IM 卡片审批回调 | notify_message, notify_subscription, notify_rule, channel_config, im_identity_binding, im_card | iam, wf | `im.binding.changed` `im.callback.rejected` | N01–N03, SYS09, SYS19–20, SYS25–26, W08 |
| 18 | 人事与薪资 `hr` | 组织、员工、入转离、考勤、请假、算薪（规则引擎）、复核、工资条、规则版本、专项附加扣除 | department, employee, attendance_record, leave_request, payroll_run(+line), payroll_rule_version, tax_deduction, payslip | iam, wf, gl | `hr.employee.offboarded` `hr.payroll.calculated/approved` | HR01–HR12 |
| 19 | 行政 `office` | 合同、固定资产（领用/归还/折旧）、公告、办公用品 | contract, asset, asset_assignment, depreciation_run, announcement, office_supply, supply_request | hr, gl | `office.contract.expiring` | AM01–AM05 |
| 20 | 知识库与新人上手 `kb` | 空间/文件夹/文档/版本、审核发布、ACL、检索与索引、问答沉淀、到期提醒、员工个人档案、上手清单与引导 | kb_space, kb_folder, kb_doc, kb_doc_version, kb_review, kb_chunk, kb_qa, employee_file, onboarding_checklist | platform, audit, agent | `kb.doc.published` `kb.sensitive.accessed` `kb.doc.expiring` | K01–K09, HR13, ON01–ON02, G10–G11 |
| 21 | 平台集成 `integ` | 连接器目录、平台授权（SP-API/Shopify/领星）、导入向导、同步任务、账套目标（金蝶/ERPNext）、集成日志 | connector, platform_auth, import_wizard_session, sync_job, ledger_target, integration_log | fin, catalog, sales, ledger | `integration.sync.finished` | INT01–INT05, SYS06 |
| 22 | 智能体中心 `agent` | AI 总开关、智能体档案、会话/消息/运行/步骤、建议生命周期、定时任务、提示词、评测、用量预算、工具注册表（ERP/联网/MCP/HTTP）、MCP 服务器、自主等级、票据收件箱、主动提醒、可信度、范围收窄、模型设置（OpenAI 兼容）、委托通行证（系统自动管理） | agent_definition, agent_tool, agent_tool_grant, conversation_thread, message, agent_run, agent_run_step, agent_suggestion, agent_task, autonomy_policy, ai_mode_state, mcp_server, model_config, delegation, llm_call… | 全部业务模块（只读直接用；低/中风险自动执行；高风险起草待审）, wf, audit | `agent.suggestion.*` `agent.mode.changed` `agent.run.finished` | G01–G26, W05 |
| 23 | 本体与实体目录 `onto` | 实体类型、动作类型、事件类型目录（只读，由各模块 manifest 生成）；动作预检；实体版本与溯源查询 | entity_type, action_type, event_type, entity_version | platform, iam | `entity.versioned` | 无独立页面，嵌入 SYS03、U01、F02、F05、G01、G04、G06、G24（详情页「版本/来源」、agent 工具目录） |
| 24 | 数据进入与溯源 `ingest` | 原件落地、清洗校验、去重与实体对齐、映射规则、投射到实体、按批次重放 | ingest_batch, raw_record, cleansing_issue, mapping_rule, dedup_candidate | platform, onto, 各业务模块的动作 | `ingest.batch.projected` `ingest.issue.raised` | F01–F02, F16–F17, AD02, P08, INT01–INT02, INT05（复用现有导入页） |
| 25 | 数字孪生与推演 `twin` | 孪生状态与同步、偏差核对与纠偏草稿、快照与按时点回看、推演副本与转草稿 | twin_state, twin_drift, twin_snapshot, twin_scenario | ingest, inv, logi, fin, catalog, hr | `twin.drift.detected` `twin.scenario.promoted` | D01, D03, I02, I13, I17, I20, F06, F10, F22, F25, INT02, INT05（嵌入现有页面） |

### 3.1 核心状态机（完整状态机见 [`08/ontology-entities.yaml`](08/ontology-entities.yaml) 中每个实体的 `stateMachine`，共 500 个动作，「状态迁移没有对应动作」的缺口为 0）

所有新单据用两层状态：`docstatus` 0 草稿 / 1 已提交 / 2 已取消，加业务状态（07 第 0.4 节）。已过账的凭证和库存流水只追加，**取消已过账单据的唯一路径是红字冲销**。

| 对象 | 状态流转 |
|---|---|
| 审批单（现有，扩展） | draft → pending →（多级 step）→ approved / rejected；approved → exported；rejected → draft；**新增** pending → withdrawn（提交人撤回，推断）；**v4**：提交时由审批人解析器分流，draft → pending（有审批人）/ auto_effective（无审批人，直接生效并留痕）/ awaiting_initiator（AI 发起的高风险或钱账动作无审批人，等发起人本人确认）→ approved |
| 凭证 | draft → pending → approved → posted；posted 不可改，只能生成全额红字冲销凭证（draft→…→posted），双向关联 `reverses/reversedBy` |
| 采购单 | draft → pending → approved → partially_received → received → closed；draft/pending/approved（未收货）→ cancelled |
| 库存单据（入/出/调拨） | draft → posted（生成流水与成本层）；posted 只能红字 |
| 盘点单 | draft → counting → submitted → approved → posted（盘盈亏凭证草稿） |
| 头程运单 | planned → in_transit（在途物资）→ arrived（转库存）→ closed；费用 → 到岸成本分摊单 draft → pending → approved → posted |
| 补货计划 | running → ready →（行 frozen / converted→采购单草稿）→ superseded（新版本生成时） |
| 会计期间 | open → closing（清单检查）→ closed → reopen_requested → reopened（反结账审批通过，申请人不能自批）→ closed |
| 期初批次 | draft → imported → balanced（试算平衡）→ pending → activated（锁定） |
| 报销单 | draft → pending（按金额多级）→ approved → paid；rejected → draft |
| 薪资批次 | calculated → reviewed → pending → approved → published → locked；修改只能走更正批次 |
| AI 建议 | proposed → submitted（进审批）→ approved / rejected → executed；L3：executed → undone（24 小时内）；proposed → expired / dismissed |
| 知识文档 | draft → in_review → published → archived；新版本走同一审核 |
| 导入批次 | v2 改用 `IngestBatch`：uploaded → landed（原件落地）→ cleansed（清洗校验、去重）→ projected（投射成实体）；landed/cleansed → failed（可重试）；projected → superseded（重放）；见第 9.3 节 |

### 3.2 主业务链与事件（在 02 第 5、12.3 节基础上补充）

```text
补货计划(inv) ─convert→ 采购单(proc) ─approve→ 收货(proc) ─event receipt.confirmed→ 入库流水+成本层(inv) + 暂估应付(gl)
头程运单(logi) ─depart→ 在途 ─arrive→ 库存；头程费用 → 到岸成本分摊单(gl) ─approve→ 成本层重估
订单(sales) ─ship→ 出库流水(inv) ─月末→ 成本结转运行(gl) → 结转凭证草稿 → 审批 → ledger 过账/导出
平台结算导入(fin) → 对账 → 异常/利润 → 结算清分 → 凭证草稿(gl) → 审批 → ledger
采购发票到 → 冲暂估 → 应付(fin) → 付款申请 → 审批 → 核销
```

新增事件（推断）：`inventory.valuation.posted`、`logistics.shipment.arrived`、`accounting.landed_cost.approved`、`accounting.period.reopened`、`accounting.opening.activated`、`agent.run.cancelled`（登出/切换账号作废）。事件先做进程内同步/后台调用，与业务修改在同一事务边界内（02 第 5 节）。

---

## 4. 跨切面设计

### 4.1 认证与会话

- 浏览器：沿用现有会话 Cookie（`HttpOnly`、`SameSite=Lax`，生产 `Secure`）+ CSRF 头 `X-CSRF-Token`。沿用现有配置：失败 5 次锁 15 分钟、会话 12 小时、空闲 2 小时（`config.py`）。
- 脚本：API Token（`Authorization: Bearer`，只存哈希，明文只显示一次；现有 `auth/tokens.py`）。
- agent（DeerFlow SDK，在独立的 agent worker 进程内）调用 CrossERP 工具：**委托通行证**（`Delegation`），由系统自动签发、静默续期、自动作废，用户无感（第 10.5 节）；通过进程内传递，没有网络令牌。
- `GET /auth/me` 是前端会话和权限的唯一来源，返回有效权限点、数据范围、字段策略、AI 模式、本位币和时区。真实模式下去掉前端的「演示角色切换」。
- 登出：`POST /auth/logout` 作废会话，**同时作废该会话的委托通行证，并停止还在进行中的智能体运行**（守卫中间件拦截下一步；服务端按 session_id 自动处理，前端不需要额外调用）；前端照现有约定整页刷新。

### 4.2 权限表

- **权限点目录**：以前端 `permissionCatalog`（811 点，`doctype:action`，含字段级）为准，由各模块 manifest 注册入库。旧的 15 个后端权限点通过映射表兼容，例如 `report.read` → `report:read`、`approval.decide` → `approval:approve`，测试不删。
- **角色**：可新建、复制、停用；16 个预置模板 + 5 个旧角色作为种子数据。支持多层继承，禁止循环；一人可挂多个角色。
- **有效权限** = 继承链上的所有「允许」∪ 用户例外 ∪ 未过期的临时授权，再减去任一来源的显式拒绝（**拒绝优先**）。数据范围取各角色并集，再与 AI 收窄规则取交集；字段权限在序列化时去掉，不靠前端隐藏（02 第 13 节）。
- **每个接口都是一个实体动作的投影**（`x-crosserp.entity/action`），动作在实体目录里绑定权限点。每个接口在路由声明 `x-permission`（见 OpenAPI 的 `x-crosserp.permission`），由统一依赖 `require(perm)` 校验。数据范围由仓储层统一注入过滤条件（店铺 / 部门 / 本人 / 负责人 / 仓库 / 金额门槛）。列表、详情、导出、AI 工具调用都走同一个过滤函数。
- **无权与不存在一律返回 404**，防止枚举。超出范围的写操作返回 403 `DATA_SCOPE_DENIED`。

### 4.3 AI 的身份与权限

- AI 动作一律记录 `actor_type=agent`、`agent_id`、`on_behalf_of_user_id`。
- **AI 继承当前登录账号的全部有效权限，不会更多**，包括功能、字段和数据范围。管理员可以按智能体或工具再收窄（只能收窄）。
- **动作护栏**和用户权限是两回事。即使用户自己有权限，AI 代做时也必须遵守：
  - 改账的动作（生成凭证、调账、过账、付款、核销等）最高 L2，钱和账的只读查询不受限；
  - 审批决定只能由真人做；
  - 改权限、改自主等级、改日志保留、改模型设置只能由真人做（查看可以）；
  - 不能自批，做单的人不能审单。
- 前端发起时快照发起人（userId + role），服务端以会话身份为准再比对一次，不一致返回 409 `AI_INITIATOR_MISMATCH`，并作废这次运行。现有前端的 bindInitiator 约定由服务端强制执行。
- **v3/v4**：身份通过委托通行证带进 DeerFlow（ID 放在 `authz_attributes`，子智能体自动继承），每次工具调用都在 CrossERP 按被代表人当时的权限重新判定。权限一变（权限版本 +1），旧通行证立即作废、当前运行停止；用户下次发消息时系统按新权限静默重新签发，不报错。完整链路、通行证设计、风险分级、防扩权规则见第 10 章。

### 4.4 AI 自主等级与风险分级（v4：只看动作改不改数据）

**v4 分级原则（maken 第 2、7 条）**：分级只看一个问题——这个动作会不会改动数据。
- **只读动作一律归「无（只读）」**，AI 可以直接用。这包括钱和账的查询：对账结果、利润、凭证、余额、报表、薪资批次、审计记录等。AI 读到什么，取决于被代表人自己能看什么：数据范围和字段策略照常生效（例如没有薪资权限的人，AI 也读不到薪资）。
- **对账拆成两段**：对账的计算、匹配、差异分析不改账，属于只读或低风险，AI 直接做；只有**生成凭证、调整账务**时，才受「钱和账最多到起草、待审」的限制。
- **中风险不设次数限额**，保留「可撤销」和「事后通知」。通知只进每天一条站内摘要，不弹窗、不推送 IM 或邮件，用户可以关掉。
- 每个动作的级别写在实体目录（[`08/ontology-entities.yaml`](08/ontology-entities.yaml) 的 `riskTier`）和 OpenAPI（`x-crosserp.riskTier`）里。

| 风险 | 自主等级 | agent 能做什么 | 接口标注 | v3 数量 | **v4 数量** |
|---|---|---|---|---|---|
| 无（只读） | L1 | 直接查询、解释、提醒（含钱和账的查询） | `R` | 224 | **258** |
| 低 | L3 | 直接执行；不改业务数据，或只产生可重算的派生结果；**不设次数上限** | `L3` | 34 | **37** |
| 中 | L3 | 直接执行；改数据但不改账；24 小时内可撤销；**不设次数限额**；事后只进每日站内摘要 | `M3` | 73 | **74** |
| 高 | L2 | 可以发起，结果是草稿或待审项（`origin=agent`），按第 4.6 节审批规则生效 | `L2` | 57 | **56** |
| 危 | L0 | agent 禁用（不可调用 / 仅真人） | `N` / `H` | 142 | **104** |
| 合计 | | | | 530 | **529** |

**v3 → v4 调整明细（共 36 个接口改级，另有增删）**：
1. **33 个只读接口从「危」改回「只读」**（全部是 GET，不改任何数据）：
   - 系统与权限 15 个：我的 API Token 列表、我的登录会话、用户列表/详情、有效权限解释、角色列表/详情、权限点目录、权限矩阵、字段权限、数据范围、临时授权、权限复核任务、职责分离规则、系统参数；
   - 审计 6 个：哈希链头、审计包下载、安全日志、日志保留策略、归档运行记录，以及报表结果导出（`GET /reports/runs/{runId}/export`）；
   - 人事与薪资 6 个：薪资批次列表/详情、社保公积金个税规则、专项附加扣除、我的工资条、员工个人档案；
   - IM 3 个：我的 IM 绑定、IM 审批设置、IM 卡片预览；
   - 其他 3 个：账套导出目标设置、LLM 调用记录列表/详情。
   - 唯一没改的 GET：`/im/bindings/{channel}/oauth-callback`。它虽然是 GET，但会完成账号绑定（改数据），而且是外部回调，仍为「危」。
2. **3 个不改数据的写接口降为「低」**：生成审计包（`POST /audit/exports`，只读导出）、测试调用工具（`POST /agent/tools/{id}/test`）、测试模型连通（`POST /agent/model-config/test`，原「测试 DeerFlow 连通」）。
3. **1 个对账接口从「高」降为「中」**：处理对账差异（`POST /finance/issues/{id}/resolve`，标「已解释/忽略」）。它只改差异本身的状态，不改账；原因由 AI 预填，人可以直接确认。由差异**生成调整凭证**（`/finance/issues/{id}/draft-voucher`）仍是「高」。
4. **对账链上各接口的级别**：触发对账（计算、匹配）= 低；差异自动打标签 = 低；对账结果、差异、利润、凭证、余额、报表查询 = 只读；处理差异 = 中；生成调整凭证、清分生成凭证、核销提交 = 高；导出写账 = 危。
5. **增删**：删除 3 个（签发委托、作废委托、DeerFlow 回写回调；均为「危」）；新增 2 个（发起人确认 = 仅真人，审批人预览 = 只读）。

**钱和账的硬上限只管「改账」**：生成凭证、调账、过账、结转、付款、核销、薪资计算与发布、导出写账，AI 最多到起草、待审；删除一律 L0（只作废不删）。即使数据库里配成更高，执行时也会自动降级，并写一条安全日志（05 第 3 节）。管理员只能把某个动作收紧，不能放宽。v3 的「中风险目标涉及钱和账实体时运行时降为 L2」取消：改账的动作本来就定为「高」，不改账的（例如处理对账差异）不再因为碰到财务实体而升级。

- 低风险（37 个）：打标签/归类、已读、对账计算与匹配、补货计划、试算、齐套校验、供应商评分、报表运行、建内部工单/跟进、重建索引、测试连通、发起只读同步、票据分类、评测、知识编译与体检、孪生快照、推演副本新建/试算/归档、生成审计包。
- 中风险（74 个）：非钱账主数据（SKU、Listing、类目、品牌、仓库、物流商、运费模板）、业务草稿（采购单、询价、合同、运单、退货登记、库存单据草稿）、CRM、知识页草稿、导入落地与投射、清洗问题处理与去重合并、孪生偏差处理与转交、对账差异处理。完整清单见第 5 节 AI 列。
- 降级模式（模型报错、预算到 80%、管理员切换）：所有接口按只读处理，L3 暂停；恢复正常只能由人手动操作。

### 4.5 统一操作日志

- 继续使用现有 `audit_log` 哈希链，追加列（02 第 14.2 节）：actor_type、agent_id、on_behalf_of、channel（web/feishu/wecom/mcp/system）、request_id、diff（敏感字段只记「已修改」）、evidence、approval_id、AI 专属字段（模型、提示词版本、run、llm_call、工具调用、把握度、自主等级）。
- 非 GET 接口共 275 个，其中 269 个记日志。不记的 6 个都不改业务数据：标记已读 2 个、导入预览、上手问答、提醒已读、动作预检。敏感读取也记日志，共 18 个（GET 17 个 + 个人档案下载 1 个），包括薪资、个人档案、敏感文档、审计包、调用详情，以及 v2 新增的原件读取和溯源查询。
- **v2/v3**：日志里 agent 的操作另记 `delegation_id`、`run_id`、`tool_call_id`、`is_subagent` 与子智能体名。每次实体变化同时写一条 `EntityVersion`（变更前后、来源批次与原件、触发动作），与日志同一事务。日志只追加，不提供删除接口。
- 实现方式：在 `platform` 中间件里生成 request_id；服务层通过 `audit.record(...)` 写日志，与业务修改**同一事务**提交。

### 4.6 审批规则与职责分离（v4：审批人从流程配置解析，maken 第 5 条）

**一句话**：配置了审批人就必须审，谁都一样；没配置或找不到能审的人，就直接生效，但要留痕；AI 发起的高风险或钱账动作找不到审批人时，退回发起它的本人确认。

审批人解析器 `ApproverResolver` 在单据提交时运行（`Approval` 由业务单据的 submit 创建）：

1. **读流程配置**（`/workflow/rules`）：按审批类型取步骤，每步的审批人可以是指定用户、角色、部门主管、申请人上级或默认审批人。每张审批单记下所用规则的版本 `ruleId`。
2. **解析成可用账号**：账号在职、未停用、有审批权限、数据范围覆盖这张单；**排除提交人、被代表人**（AI 代谁做的，那个人也不能审）。
3. **按结果分三种**（写进 `Approval.resolution`）：

| 情况 | 结果 | 留痕 |
|---|---|---|
| 配置了审批人，且至少解析到 1 个可用账号 | **必须走审批**（`pending`），法人或老大提交也一样；只能由解析出的人审批，自己不能审批自己提交的单 | 正常审批记录 |
| 没有配置审批人，或解析不到可用账号（例如 3 人团队没有人事主管；或者配置的审批人就是提交人本人，排除后没人） | 人发起的单据：**免审批直接生效**（`auto_effective`），照常走原有的过账、写账服务 | 操作日志记「无审批人，直接生效」，附原因码（`no_rule` 未配置 / `no_account` 找不到账号 / `only_self` 只有本人）、规则版本、解析快照；进哈希链；审批中心可按「无审批人生效」筛选追溯 |
| 同上，但单据由 **AI 发起**，且是高风险或涉及钱和账 | **不直接生效**：退回发起它的本人确认（`awaiting_initiator`），本人在「我提交的」或「智能体建议」里点一次「确认生效」（`POST /approvals/{id}/initiator-confirm`），确认后才生效 | 记「无审批人，发起人确认」，附确认人、时间、内容哈希；AI 不能调用确认接口（仅真人） |

4. **多级审批**：每一步单独解析。解析不到人的那一步跳过并记「该步无审批人」；所有步骤都跳过时，按上表第二、三行处理。
5. **反结账**与上面对齐：配置了审批人就走审批，申请人不能自批；没配置时按免审批处理并留痕。期末结账本身仍只能由真人操作。
6. **提交前就能看到结果**：`GET /workflow/rules/resolve` 返回「将由谁审批」「无审批人，提交即生效」或「需要你本人确认」，前端在提交按钮旁直接显示，用户不用猜。
7. **开箱即用**：预置流程模板的审批人默认留空（演示默认值），所以小团队装好就能用，不会被审批卡住；管理员配好审批人后立即按新规则执行。修改流程配置只能由真人操作（`PUT /workflow/rules/{id}`），并写日志。
8. **审批不设金额上限**（v3 已定）：有审批权限、被流程解析到就能批。

职责分离：
- 统一在 `POST /approvals/{id}/decide` 执行：提交人、被代表人、起草草稿的 AI 所代表的人，都不能审批同一张单；内容哈希必须一致。
- 前端里的反结账、需求因子、到岸成本分摊、盘点、薪资（发起人和复核人都不能审批）都注册为审批类型，规则相同。可配置的互斥规则 `sod_rule` 保留，例如「新建供应商」与「发起付款」不能是同一人；互斥规则导致找不到可用审批人时，同样按「无审批人」处理并留痕。
- **v1 的「单人模式」取消**，由上面的规则代替：没有别人能审时直接生效（人发起）或本人确认（AI 发起），都有记录。

### 4.7 传统流程保底

- 每个 L2 动作都有对应的人工接口和页面，AI 只是预先填好草稿。AI 关闭时（`PUT /agent/mode` → off），除智能体中心外的所有接口照常可用。智能体相关接口返回 409 `AI_MODE_OFF`，页面隐藏 AI 区域。
- 回归要求：AI 开和关两种状态各跑一次全部点击验证，沿用现有 21 角色 × AI 开/关 的回归套件。

### 4.8 幂等、并发、分页、错误码

- **幂等**：所有 POST 接受 `Idempotency-Key`（24 小时内同键同请求体返回第一次的结果；同键不同请求体返回 409）。导入另外按文件 SHA-256 去重（现有）。审批决定、导出、过账、算薪必须带这个头。
- **并发**：可修改的资源带 `version`，写请求传 `expectedVersion`，不一致返回 409 `CONFLICT_VERSION`（与现有审批乐观锁一致）。
- **分页**：`page`、`pageSize`（≤200），返回 `{items,page,pageSize,total}`；导出类大列表走后台任务（`202 + Job`）。
- **错误**：`{code,message,details,requestId}`，`code` 取自 OpenAPI 的 `ErrorCode` 枚举（30 个；v2 新增 `DELEGATION_INVALID`、`DELEGATION_SCOPE_EXCEEDED`、`PERMISSIONS_CHANGED`、`SCENARIO_READ_ONLY`），例如 `SOD_VIOLATION`、`PAYLOAD_HASH_MISMATCH`、`PERIOD_CLOSED`、`LEDGER_UNBALANCED`、`PLACEHOLDER_ACCOUNT_CODE`、`AI_AUTONOMY_CAPPED`。不向浏览器返回堆栈。
- **JSON 命名**：字段用 camelCase，与前端 `src/types` 一致；Python 内部用 snake_case，由 Pydantic `alias_generator` 自动转换。注意：02 第 6 节原写的是 `page_size`，本设计改为 `pageSize`，以前端为准。

### 4.9 金额、币种、时区

- **金额**：一律用 `Money = {amountMinor: int64, currency}`，`amountMinor` 为**万分位整数**（SCALE=10000）。这与前端 `utils/money.ts` 的 `Minor` 和后端 `Money4` 一致，不用浮点。移动加权单价、汇率这类需要更高精度的值用十进制字符串。
- **需要统一**：HR 类型里的 `*Cents`（分）和部分 `amount: number`，在接入真实接口前要统一成 `Minor`。前端已有 `minorFromCents`，可在适配层转换。
- **币种**：本位币 CNY；原币与本位币金额都要存。汇率来源分两类：月汇率（现有 `fx_rate`，给利润快照用）和日汇率（新表，给过账用）。结算清分 v1.0 使用结算单结束日的单一汇率（07 第 A-5.3、B-5.4 节）。
- **时间**：数据库和接口一律使用 UTC（现有 `UtcDateTime`），前端按用户时区（默认 Asia/Shanghai）显示。会计期间按北京时间自然月切分（推断，需会计确认）。

### 4.10 智能体接入（DeerFlow 2.0，SDK 嵌入；v4：独立 worker、OpenAI 兼容模型、禁止执行代码）

- **不单独部署 DeerFlow**。在 CrossERP 的 **agent worker 进程**里用 `deerflow.client.DeerFlowClient` 运行（核实见第 10.0 节）。v4（maken 第 1 条）：agent worker 是**独立进程、独立 Python 虚拟环境**，DeerFlow 的约 350 个依赖不进 CrossERP API 进程；两者通过 MySQL 任务表和事件表通信（第 10.1 节）。
- CrossERP 注册 5 个进程内工具：`crosserp_describe`、`crosserp_query`、`crosserp_dry_run`、`crosserp_execute`、`crosserp_lineage`。它们直接调用 `ActionDispatcher`，可执行范围由服务端按委托计算。现有 9 个只读工具并入这 5 个工具；`mcp_server` 保留给外部客户端用（可选）。
- **模型**：兼容 OpenAI 接口（`baseUrl`、`apiKey`、`model`），在前端「模型设置」页填写；`apiKey` 加密存储、不回显、不写日志；worker 在运行时把配置交给 DeerFlowClient（第 10.8 节）。原「DeerFlow 接入」页（G17）改为「模型设置」页；v3 的 `/agent/deerflow*` 三个接口改为 `/agent/model-config*`，回写回调接口删除（SDK 模式下 worker 直接写库）。
- **禁止 AI 执行代码**（maken 第 8 条）：不配置 bash 和文件读写工具，宿主机 bash 关闭，不装 Docker，不用任何代码沙箱；以后的脚本库只能注册成功能函数或 MCP 工具（第 10.9 节）。
- 预留的智能体数据增删改查都在智能体中心模块：档案、会话、消息、运行、步骤、建议、任务、提示词、评测、工具、范围收窄。委托通行证由系统自动管理，**没有面向用户的页面和接口**，只有管理员审计用的只读列表。
- **工具可配置，包括联网检索**（`kind=web`）：联网结果一律当作数据，不当作指令；引用必须带网址和抓取时间；不能只凭联网结果触发写动作（02 第 12.4 节）。
- 聊天接口 `POST /agent/threads/{id}/messages` 用 SSE 流式返回，事件包括 token、tool_call、citation、suggestion、done。事件由 worker 写入，API 进程推送。用户点「停止」或登出时停止这次运行。
- 定时任务由 CrossERP 调度器触发（v3 已定）。

### 4.11 可插拔扩展点：通知、审批渠道、平台接入、外部账套（v4，maken 第 9 条）

**v4：IM 审批延后，先只做平台内渠道**；但审批、通知、平台接入、外部账套、以后的脚本库都按同一种「适配器」模式设计。以后接 IM、邮件或别的系统，只需要新增一个适配器，不改业务代码。

**统一约定（所有扩展点都遵守）**：
1. **注册方式**：每个适配器是一个 Python 包，通过 entry point 注册到对应分组（`crosserp.channels`、`crosserp.connectors`、`crosserp.ledger_targets`、`crosserp.functions`），并带一份清单 `manifest`：`key`、`version`、`capabilities`、`configSchema`（JSON Schema）、`secrets`（只声明名字）、需要的权限点。前端设置页按 `configSchema` 自动生成表单，管理员只填必要项，不用写配置文件。
2. **业务逻辑不进适配器**：适配器只做「格式转换 + 收发」。任何会改数据的动作都回到 `ActionDispatcher` 或既有服务（审批决定 → `approvals.decide`；入账 → ledger 唯一出口；外部数据 → `IngestBatch` 原件落地），权限、职责分离、风险分级在那里统一检查。
3. **可靠投递**：对外发送一律走 outbox，与业务修改同一事务写入，worker 异步发送；有幂等键 `dedupKey`、超时、指数退避重试（演示默认 3 次）；发送失败不回滚业务，只记失败并在管理员健康页显示。
4. **回调安全**：外部回调统一检查签名 → 时间戳与防重放 → 身份绑定 → 内容哈希 → 服务端重新校验权限。
5. **密钥**：只存 secret-ref，加密存储，不回显、不写日志（与第 10.8 节模型密钥同一机制）。
6. **留痕**：日志的 `channel` 字段记录来源（`web`、`inapp`、`feishu`、`wecom`、`email`、`mcp`、`system` 等）。
7. **健康检查**：每个适配器实现 `health_check()`，结果显示在对应设置页。

**四类扩展点的接口**（Python 协议，示意；实现时以代码为准）：

| 扩展点 | 接口 | 首期实现 | 以后可接 | 对应接口 |
|---|---|---|---|---|
| 通知渠道 `NotificationChannel` | `capabilities()`；`send(msg: OutboundMessage) -> DeliveryResult`；`health_check()`；可选 `bind_identity / resolve_identity / verify_callback` | **站内**（消息中心 + 待办 + 每日摘要） | IM、邮件、Webhook | `/notify/*` |
| 审批渠道 `ApprovalChannel`（继承通知渠道） | `send_approval_card(approval, approver)`；`parse_decision(callback) -> DecisionCommand`（只能产出决定命令，交给 `approvals.decide`） | **平台内审批页** | 飞书、企业微信、钉钉卡片（P5 之后） | `/approvals/*`、`/im/*` |
| 平台接入 `PlatformConnector` | `capabilities()`；`pull(resource, since) -> Iterator[RawRecord]`；`health_check()`；首期不做 `push` | 文件导入 → Amazon → Shopify → 领星（v3 已定） | 其他电商平台、ERP | `/integrations/*`、`/ingest/*` |
| 外部账套 `LedgerTarget` | `map_voucher(voucher) -> payload`；`export(batch) -> ExportResult`；`fetch_status(exportId)`；`test()` | 金蝶 → 用友 → 其他（v3 已定） | 其他财务软件 | `/integrations/ledger-targets/*`、`/finance/vouchers/{id}/exports` |
| 功能函数 / 脚本库 `RegisteredFunction`（第 10.9 节） | `manifest`（输入输出 JSON Schema、权限点、风险级别）；`run(params, ctx)` | 无 | 开发者审核后注册的脚本 | 作为实体动作或 MCP 工具暴露 |

**统一消息格式 `OutboundMessage`**：`recipientUserId`、`kind`（todo 待办 / digest 摘要 / alert 告警）、`title`、`body`（Markdown，≤500 字）、`links`、`dedupKey`、`priority`（normal / low）。通知路由器按 `kind` 和用户偏好选择渠道。首期只有站内渠道，所以所有消息都进消息中心；以后接了 IM，用户在偏好里勾选即可。

**通知要简洁，不打扰**：
- AI 自动做的低、中风险动作：**不逐条通知**，每天汇总成一条站内摘要（「AI 今天替你做了 N 件事」，每条可一键撤销），不弹窗、不推送；用户可以关掉摘要。
- 高风险草稿：作为普通待办出现在审批中心或「我提交的」，不另发通知。
- 异常检测（例如短时间内大量被拒）：只告诉管理员，不打扰普通用户。

IM 审批的后期设计保持不变：身份绑定 `/im/bindings/*` 走官方授权回调，一个 IM 账号只能绑一个用户，离职自动解绑；卡片回调 `POST /im/callbacks/{channel}` 通过上面的回调安全检查后，调用与网页**完全相同**的 `approvals.decide` 服务。各开放平台的具体接口名「未核实」。

---

## 5. API 清单（529 个）

说明：
- **每个接口都是某个实体动作的投影**。「实体动作」列写成 `实体.动作`；实体和动作的定义、状态机、权限点见 [`08/ontology-entities.yaml`](08/ontology-entities.yaml)。同一个动作可以有多个接口，例如列表和导出。
- 下表省略了路径前缀 `/api/v1`。
- 「页面」列是对应的前端页面 ID。
- 「日志」列：记 = 写操作日志；敏感读也记 = 读取也写日志；— = 不记。
- 「AI」列（v4 风险分级，第 4.4 节：只看动作改不改数据）：可读（L1，含钱和账的查询）/ 低风险：自动执行（L3）/ 中风险：自动执行，可撤销，不设次数限额（L3）/ 高风险：可做，须按审批规则生效（L2）/ 仅真人 / 不可。
- 「来源」列：已有 = 现有后端服务可直接包成 JSON；前端已声明 = 前端 service 注释里已写；推断 = 本次新增。v2 新增 55 个、v3 新增 2 个、v4 新增 2 个（发起人确认、审批人预览），均为推断（第 9.2 节）；v4 另删除 3 个（签发委托、作废委托、DeerFlow 回写回调），3 个 `/agent/deerflow*` 改为 `/agent/model-config*`。
- 请求体、响应结构、幂等头、错误响应见 [`08/openapi-draft.yaml`](08/openapi-draft.yaml)。每个操作都带 `x-crosserp` 扩展，内容包括实体、动作、权限点、日志、AI 可调用性与自主等级上限、对应页面、对应前端函数。

各模块统计：

| 模块 | 实体类型 | 接口数 | 其中写操作 | AI 可读 | 高风险起草待审(L2) | 中风险自动(L3) | 低风险自动(L3) | 仅真人/不可 | 已有服务可复用 |
|---|---|---|---|---|---|---|---|---|---|
| 平台底座 | 6 | 22 | 12 | 10 | 0 | 0 | 1 | 11 | 6 |
| 系统与权限 | 11 | 35 | 20 | 15 | 0 | 0 | 0 | 20 | 4 |
| 操作日志与审计 | 5 | 14 | 5 | 9 | 0 | 0 | 2 | 3 | 6 |
| 工作台与报表 | 2 | 10 | 2 | 8 | 0 | 1 | 1 | 0 | 0 |
| 商品与主数据 | 8 | 28 | 18 | 10 | 2 | 15 | 0 | 1 | 4 |
| 订单与售后 | 4 | 12 | 6 | 6 | 3 | 2 | 1 | 0 | 2 |
| 库存与补货 | 9 | 28 | 15 | 13 | 4 | 7 | 2 | 2 | 0 |
| 采购与供应商 | 9 | 32 | 19 | 13 | 9 | 8 | 1 | 1 | 0 |
| 物流与头程 | 5 | 17 | 11 | 6 | 4 | 6 | 1 | 0 | 0 |
| 平台结算、对账与资金 | 14 | 34 | 10 | 24 | 6 | 2 | 2 | 0 | 24 |
| 总账与成本核算 | 8 | 31 | 15 | 16 | 10 | 0 | 1 | 4 | 5 |
| 税务 | 2 | 6 | 4 | 2 | 1 | 1 | 1 | 1 | 0 |
| 费用报销与预算 | 5 | 24 | 16 | 8 | 9 | 1 | 1 | 5 | 0 |
| 广告 | 4 | 6 | 2 | 4 | 1 | 1 | 0 | 0 | 0 |
| CRM 与客服 | 8 | 24 | 11 | 13 | 1 | 6 | 4 | 0 | 0 |
| 审批中心 | 3 | 9 | 4 | 5 | 0 | 0 | 0 | 4 | 3 |
| 通知与 IM 插件 | 8 | 20 | 11 | 8 | 0 | 0 | 3 | 9 | 0 |
| 人事与薪资 | 9 | 24 | 14 | 10 | 0 | 1 | 0 | 13 | 0 |
| 行政 | 6 | 15 | 10 | 5 | 3 | 6 | 0 | 1 | 0 |
| 知识库与新人上手 | 8 | 35 | 19 | 17 | 1 | 6 | 4 | 7 | 0 |
| 平台集成 | 6 | 13 | 8 | 5 | 0 | 2 | 3 | 3 | 1 |
| 智能体中心 | 20 | 55 | 28 | 30 | 0 | 2 | 5 | 18 | 9 |
| 本体与实体目录 | 4 | 8 | 1 | 8 | 0 | 0 | 0 | 0 | 0 |
| 数据进入与溯源 | 5 | 12 | 6 | 6 | 1 | 4 | 0 | 1 | 0 |
| 数字孪生与推演 | 4 | 15 | 8 | 7 | 1 | 3 | 4 | 0 | 0 |
| **合计** | **166** | **529** | **275** | **258** | **56** | **74** | **37** | **104** | **64** |

### 5.1 平台底座（`platform`，22 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `POST /auth/login` | `UserAccount.login` | 账号密码登录，建立会话 Cookie 并返回 CSRF 令牌 | A01 | `public` | 记 | 不可 | 已有 |
| `POST /auth/logout` | `UserAccount.logout` | 退出登录，作废会话并作废该会话发起的进行中智能体请求 | A01,D01 | `authenticated` | 记 | 不可 | 已有 |
| `GET /auth/me` | `UserAccount.read_me` | 当前用户、角色、有效权限点、数据范围、AI 模式（前端 session/permission store 的唯一来源） | A02,D01,ME01 | `authenticated` | — | 可读（L1） | 推断 |
| `POST /auth/forgot-password` | `UserAccount.forgot_password` | 发起找回密码（发邮件链接，阶段：later） | A04 | `public` | 记 | 不可 | 推断 |
| `POST /auth/reset-password` | `UserAccount.reset_password` | 凭一次性令牌重置密码（阶段：later） | A05 | `public` | 记 | 不可 | 推断 |
| `GET /account/profile` | `UserAccount.list` | 我的资料 | SYS11 | `user:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /account/profile` | `UserAccount.update` | 修改我的资料（显示名、语言、时区） | SYS11 | `user:write` | 记 | 不可 | 推断 |
| `POST /account/password` | `UserAccount.create` | 修改密码 | A06 | `user:write` | 记 | 不可 | 前端已声明 |
| `GET /account/tokens` | `ApiToken.list` | 我的 API Token 列表（只显示名称和前缀） | SYS12 | `user:read` | — | 可读（L1） | 已有 |
| `POST /account/tokens` | `ApiToken.create` | 新建 API Token（明文只返回一次） | SYS12 | `user:write` | 记 | 不可 | 已有 |
| `POST /account/tokens/{id}/revoke` | `ApiToken.revoke` | 吊销 API Token | SYS12 | `user:write` | 记 | 不可 | 已有 |
| `GET /account/sessions` | `UserAccount.list` | 我的登录会话 | SYS13 | `user:read` | — | 可读（L1） | 已有 |
| `DELETE /account/sessions/{id}` | `UserAccount.delete` | 强制下线某个会话 | SYS13 | `user:write` | 记 | 不可 | 推断 |
| `GET /me/data-scope` | `UserAccount.read_data_scope` | 我的数据范围说明（店铺/部门/本人）及按范围过滤后的示例计数 | ME01 | `user:read` | — | 可读（L1） | 推断 |
| `POST /files` | `FileObject.create` | 上传文件（multipart），返回 file_id 与 SHA-256，供导入、附件、票据收件箱复用 | AD02,F01,INT01,K04 | `authenticated` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /files/{id}` | `FileObject.get` | 下载文件（按所属单据权限校验；敏感文件记访问日志） | F21,HR13,K02 | `authenticated` | 敏感读也记 | 可读（L1） | 推断 |
| `GET /jobs/{id}` | `Job.get` | 查询后台任务进度（导入、对账、同步、算薪、重建索引） | F01,HR07,INT02,K08 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /stores` | `Store.list` | 店铺列表（按数据范围过滤） | D03,SYS05 | `report:read` | — | 可读（L1） | 前端已声明 |
| `POST /admin/stores` | `Store.create` | 新建店铺 | SYS05 | `system:write` | 记 | 不可 | 推断 |
| `PATCH /admin/stores/{id}` | `Store.update` | 修改店铺（站点、币种、税务责任方） | SYS05 | `system:write` | 记 | 不可 | 推断 |
| `GET /documents/links` | `DocumentLink.read_links` | 单据关联（来源→目标） | D05 | `document:read` | — | 可读（L1） | 前端已声明 |
| `GET /documents/chain/{docType}/{id}` | `DocumentLink.read_chain` | 业务链追溯：从任一单据查出整条链和断点 | D05 | `report:read` | — | 可读（L1） | 推断 |

### 5.2 系统与权限（`iam`，35 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /admin/users` | `User.list` | 用户列表 | SYS01,SYS02 | `user_admin:read` | — | 可读（L1） | 已有 |
| `POST /admin/users` | `User.create` | 新建用户 | SYS01 | `user_admin:create` | 记 | 不可 | 已有 |
| `GET /admin/users/{id}` | `User.get` | 用户详情（角色、例外、绑定、最近登录） | SYS02 | `user_admin:read` | — | 可读（L1） | 推断 |
| `PATCH /admin/users/{id}` | `User.update` | 修改用户、停用/启用 | SYS02 | `user_admin:write` | 记 | 仅真人 | 推断 |
| `PUT /admin/users/{id}/roles` | `User.set_roles` | 设置用户角色（一人多角色） | SYS02 | `permission:write` | 记 | 仅真人 | 推断 |
| `PUT /admin/users/{id}/overrides` | `User.set_overrides` | 用户级允许/拒绝例外（带原因、有效期） | SYS02 | `permission:write` | 记 | 仅真人 | 推断 |
| `POST /admin/users/{id}/reset-password` | `User.reset_password` | 管理员重置密码 | SYS02 | `user_admin:write` | 记 | 仅真人 | 推断 |
| `GET /admin/users/{id}/effective-permissions` | `User.read_effective_permissions` | 有效权限及来源解释（角色/继承/例外/拒绝） | SYS23 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `GET /admin/roles` | `Role.list` | 角色列表（含 16 个预置模板） | SYS03 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `POST /admin/roles` | `Role.create` | 新建角色（可指定父角色继承） | SYS03 | `permission:write` | 记 | 仅真人 | 推断 |
| `GET /admin/roles/{id}` | `Role.get` | 角色详情（权限、继承链、数据范围、字段规则） | SYS21 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /admin/roles/{id}` | `Role.update` | 修改/停用角色（禁止循环继承） | SYS21 | `permission:write` | 记 | 仅真人 | 推断 |
| `PUT /admin/roles/{id}/permissions` | `Role.set_permissions` | 勾选角色权限点（允许/显式拒绝）；敏感点需第二管理员确认 | SYS03,SYS21 | `permission:write` | 记 | 仅真人 | 推断 |
| `POST /admin/roles/{id}/copy` | `Role.copy` | 复制角色 | SYS03,SYS21 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/permissions` | `PermissionPoint.list` | 权限点目录（模块 manifest 注册，三级：菜单/动作/字段） | SYS04 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `GET /admin/permission-matrix` | `PermissionPoint.list` | 权限矩阵（角色 × 权限点） | SYS22 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PUT /admin/permission-matrix` | `PermissionPoint.update` | 批量保存权限矩阵 | SYS22 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/field-policies` | `FieldPolicy.list` | 字段权限（隐藏/脱敏/只读） | SYS14 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PUT /admin/field-policies/{id}` | `FieldPolicy.update` | 保存字段权限 | SYS14 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/data-scopes` | `DataScopeRule.list` | 数据范围规则（店铺/部门/本人/仓库/金额门槛） | SYS15 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PUT /admin/data-scopes/{id}` | `DataScopeRule.update` | 保存数据范围 | SYS15 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/temp-grants` | `TempGrant.list` | 临时授权列表 | SYS16 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `POST /admin/temp-grants` | `TempGrant.create` | 新建临时授权（起止时间、原因，到期自动收回） | SYS16 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `POST /admin/temp-grants/{id}/revoke` | `TempGrant.revoke` | 提前收回临时授权 | SYS16 | `permission:write` | 记 | 仅真人 | 推断 |
| `GET /admin/access-reviews` | `AccessReview.list` | 权限复核任务 | SYS17 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `POST /admin/access-reviews` | `AccessReview.create` | 发起一轮权限复核 | SYS17 | `permission:approve` | 记 | 仅真人 | 推断 |
| `POST /admin/access-reviews/{id}/confirm` | `AccessReview.confirm` | 复核确认（保留/收回） | SYS17 | `permission:approve` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/sod-rules` | `SodRule.list` | 职责分离规则 | SYS18 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PUT /admin/sod-rules/{id}` | `SodRule.update` | 保存职责分离规则 | SYS18 | `permission:write` | 记 | 仅真人 | 前端已声明 |
| `GET /admin/modules` | `ModuleSwitch.list` | 模块开关 | SYS07 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /admin/modules/{id}` | `ModuleSwitch.update` | 启用/关闭模块 | SYS07 | `system:write` | 记 | 仅真人 | 推断 |
| `GET /admin/dictionaries` | `Dictionary.list` | 数据字典 | SYS08 | `permission:read` | — | 可读（L1） | 前端已声明 |
| `PUT /admin/dictionaries/{key}` | `Dictionary.update` | 修改数据字典项 | SYS08 | `system:write` | 记 | 仅真人 | 推断 |
| `GET /admin/settings` | `SystemSetting.list` | 系统参数（会话时长、本位币、时区） | SYS10 | `permission:read` | — | 可读（L1） | 已有 |
| `PUT /admin/settings` | `SystemSetting.update` | 保存系统参数 | SYS10 | `system:write` | 记 | 仅真人 | 已有 |

### 5.3 操作日志与审计（`audit`，14 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /audit/logs` | `AuditLog.list` | 统一操作日志（筛选：actor_type=human/agent/system、category、ref、module、on_behalf_of） | EX03,F13,K09,SYS24,U01,U03 等8页 | `audit_log:read` | 敏感读也记 | 可读（L1） | 已有 |
| `GET /audit/logs/{id}` | `AuditLog.get` | 单条日志（改前改后、证据、请求编号、哈希） | U01,U05 | `audit_log:read` | 敏感读也记 | 可读（L1） | 推断 |
| `GET /audit/chain` | `AuditLog.list` | 哈希链头与检查点 | U02 | `audit_log:read` | — | 可读（L1） | 已有 |
| `POST /audit/verify` | `AuditLog.create` | 校验哈希链完整性 | U02 | `audit_log:read` | 记 | 低风险：自动执行（L3） | 已有 |
| `POST /audit/exports` | `AuditExport.create` | 生成可离线校验的审计包（异步任务；只读导出，不改数据） | U03 | `audit_log:export` | 记 | 低风险：自动执行（L3） | 已有 |
| `GET /audit/exports/{id}/download` | `AuditExport.read_download` | 下载审计包 | U03 | `audit_log:export` | 敏感读也记 | 可读（L1） | 已有 |
| `GET /audit/security-events` | `SecurityEvent.list` | 登录与安全日志（独立哈希链） | U01,U04 | `audit_log:read` | 敏感读也记 | 可读（L1） | 已有 |
| `GET /audit/agent-trace/{suggestionId}` | `AuditLog.get` | AI 建议追溯时间轴（触发→运行→工具→证据→审批→效果） | U06 | `audit_log:read` | 敏感读也记 | 可读（L1） | 前端已声明 |
| `GET /audit/alerts` | `AuditAlert.list` | 敏感操作告警 | U07 | `audit_log:read` | — | 可读（L1） | 前端已声明 |
| `POST /audit/alerts/{id}/resolve` | `AuditAlert.resolve` | 处理告警 | U07 | `audit_log:write` | 记 | 仅真人 | 前端已声明 |
| `GET /audit/retention` | `RetentionPolicy.list` | 日志保留策略 | U08 | `audit_log:read` | — | 可读（L1） | 前端已声明 |
| `PUT /audit/retention` | `RetentionPolicy.update` | 修改保留策略（只能真人） | U08 | `audit_log:write` | 记 | 仅真人 | 前端已声明 |
| `POST /audit/retention/archive` | `RetentionPolicy.archive` | 执行归档（只归档不删除） | U08 | `audit_log:write` | 记 | 仅真人 | 前端已声明 |
| `GET /audit/retention/archive-runs` | `RetentionPolicy.read_archive_runs` | 归档运行记录 | U08 | `audit_log:read` | — | 可读（L1） | 前端已声明 |

### 5.4 工作台与报表（`dash`，10 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /dashboard/home` | `DashboardView.read_home` | 首页聚合（待办、关键指标、提醒），按角色与数据范围裁剪 | D01 | `report:read` | — | 可读（L1） | 推断 |
| `GET /dashboard/summary` | `DashboardView.read_summary` | 经营指标（store_id、period） | D01,D03 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /dashboard/periods` | `DashboardView.read_periods` | 可选期间 | D01,D03 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /dashboard/todos` | `DashboardView.read_todos` | 我的待办（审批、异常、提醒汇总） | D02 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /dashboard/calendar` | `DashboardView.read_calendar` | 经营日历（结账日、VAT 截止、合同到期、头程到港） | D04 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /reports` | `Report.list` | 报表目录 | RP01 | `report:read` | — | 可读（L1） | 前端已声明 |
| `POST /reports` | `Report.create` | 新建自定义报表定义 | RP03 | `report:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /reports/{id}` | `Report.get` | 报表定义与最近结果 | RP02 | `report:read` | — | 可读（L1） | 推断 |
| `POST /reports/{id}/run` | `Report.run` | 运行报表（只读查询） | RP01,RP02 | `report:read` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `GET /reports/runs/{runId}/export` | `Report.read_runs_export` | 导出报表结果（敏感导出触发告警） | RP02 | `report:export` | 敏感读也记 | 可读（L1） | 推断 |

### 5.5 商品与主数据（`catalog`，28 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /catalog/skus` | `Sku.list` | SKU 列表 | P01 | `item:read` | — | 可读（L1） | 前端已声明 |
| `GET /catalog/skus/{id}` | `Sku.get` | SKU 详情（成本受字段权限保护） | F11,P02 | `item:read` | — | 可读（L1） | 前端已声明 |
| `POST /catalog/skus` | `Sku.create` | 新建 SKU | P01 | `item:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /catalog/skus/{id}` | `Sku.update` | 修改 SKU | P01 | `item:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /catalog/skus/status` | `Sku.status` | 批量启用/停用 SKU | P01,P02 | `item:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /catalog/costs` | `SkuCost.list` | SKU 成本期间 | P03 | `item:read` | — | 可读（L1） | 已有 |
| `POST /catalog/costs` | `SkuCost.create` | 新增成本期间（触发利润重算提醒） | P02,P03 | `item:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `GET /catalog/listings` | `Listing.list` | 平台 Listing | P04 | `listing:read` | — | 可读（L1） | 前端已声明 |
| `GET /catalog/listings/{id}` | `Listing.get` | Listing 详情 | P05 | `listing:read` | — | 可读（L1） | 前端已声明 |
| `POST /catalog/listings` | `Listing.create` | 新建 Listing | P04 | `listing:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /catalog/listings/{id}` | `Listing.update` | 修改 Listing（负责人、状态） | P05 | `listing:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /catalog/listings/status` | `Listing.status` | 批量改 Listing 状态 | P04 | `listing:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /catalog/categories` | `Category.list` | 类目 | P06 | `item_group:read` | — | 可读（L1） | 前端已声明 |
| `POST /catalog/categories` | `Category.create` | 新建类目 | P06 | `item_group:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /catalog/categories/{id}` | `Category.update` | 修改类目 | P06 | `item_group:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /catalog/categories/status` | `Category.status` | 启用/停用类目 | P06 | `item_group:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /catalog/brands` | `Brand.list` | 品牌 | P07 | `brand:read` | — | 可读（L1） | 前端已声明 |
| `POST /catalog/brands` | `Brand.create` | 新建品牌 | P07 | `brand:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /catalog/brands/{id}` | `Brand.update` | 修改品牌 | P07 | `brand:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /catalog/brands/status` | `Brand.status` | 启用/停用品牌 | P07 | `brand:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /catalog/mappings` | `SkuMapping.list` | 平台 SKU 映射 | P08 | `listing:read` | — | 可读（L1） | 已有 |
| `POST /catalog/mappings` | `SkuMapping.create` | 新增映射 | P08 | `item:write` | 记 | 中风险：自动执行，可撤销（L3） | 已有 |
| `POST /catalog/mappings/confirm` | `SkuMapping.confirm` | 确认映射（AI 建议的映射须人确认） | P08 | `item:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /catalog/bundles` | `Bundle.list` | 组合装 | P09 | `item:read` | — | 可读（L1） | 前端已声明 |
| `POST /catalog/bundles` | `Bundle.create` | 新建组合装 | P09 | `item:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /catalog/bundles/{id}` | `Bundle.update` | 修改组合装 | P09 | `item:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /catalog/bundles/deactivate` | `Bundle.deactivate` | 作废组合装（不物理删除；原 DELETE 改为作废） | P09 | `item:delete` | 记 | 不可 | 前端已声明 |
| `GET /catalog/lookups` | `CatalogLookup.list` | 商品下拉数据（类目、品牌、店铺、币种） | P01,P03,P04,P08,P09 | `item:read` | — | 可读（L1） | 前端已声明 |

### 5.6 订单与售后（`sales`，12 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /sales/orders` | `SalesOrder.list` | 订单列表（店铺范围过滤） | ME01,O01,O03,R12 | `sales_order:read` | — | 可读（L1） | 已有 |
| `GET /sales/orders/{id}` | `SalesOrder.get` | 订单详情（含结算、出库、凭证链） | O02 | `sales_order:read` | — | 可读（L1） | 已有 |
| `POST /sales/orders/{id}/ship` | `SalesOrder.ship` | 单个订单发货（扣库存、进入待结转） | O02 | `delivery_note:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /sales/orders/ship` | `SalesOrder.ship` | 批量发货 | O01,O06 | `delivery_note:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /sales/returns` | `SalesReturn.list` | 退货退款 | O03 | `sales_order:read` | — | 可读（L1） | 前端已声明 |
| `POST /sales/orders/{id}/returns` | `SalesOrder.returns` | 登记退货 | O02,O03 | `sales_order:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /sales/returns/{id}/dispose` | `SalesReturn.dispose` | 退货处置（入库/报损），生成冲减凭证草稿 | O03 | `delivery_note:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /sales/exceptions` | `OrderException.list` | 异常订单 | O04 | `sales_order:read` | — | 可读（L1） | 前端已声明 |
| `POST /sales/exceptions/{id}/tag` | `OrderException.tag` | 给异常订单打标签/归类（白名单 L3，可撤销） | O04 | `sales_order:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /sales/channels` | `SalesChannel.list` | 多渠道汇总 | O05 | `sales_order:read` | — | 可读（L1） | 前端已声明 |
| `GET /sales/fulfillment` | `SalesOrder.list` | 履约进度 | O06 | `sales_order:read` | — | 可读（L1） | 前端已声明 |
| `POST /sales/exceptions/{id}/resolve` | `OrderException.resolve` | 关闭异常订单（写处理结论） | O04 | `sales_order:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |

### 5.7 库存与补货（`inv`，28 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /inventory/warehouses` | `Warehouse.list` | 仓库档案 | I01 | `warehouse:read` | — | 可读（L1） | 前端已声明 |
| `POST /inventory/warehouses` | `Warehouse.create` | 新建仓库 | I01 | `warehouse:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /inventory/warehouses/{id}` | `Warehouse.update` | 修改仓库 | I01 | `warehouse:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /inventory/warehouses/status` | `Warehouse.status` | 启用/停用仓库 | I01 | `warehouse:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /inventory/on-hand` | `InventoryPosition.list` | 库存总览 | I02 | `stock_ledger:read` | — | 可读（L1） | 前端已声明 |
| `GET /inventory/balances` | `InventoryPosition.list` | 分仓库存（kind=fba/overseas/domestic） | I03,I04,I05 | `stock_ledger:read` | — | 可读（L1） | 前端已声明 |
| `GET /inventory/movements` | `StockMovement.list` | 库存流水（只追加） | I06 | `stock_ledger:read` | — | 可读（L1） | 前端已声明 |
| `GET /inventory/stock-ledger` | `StockMovement.list` | 库存台账：数量、移动加权单价、结存金额（成本字段受字段权限） | I16 | `stock_ledger:read` | — | 可读（L1） | 推断 |
| `GET /inventory/docs` | `InventoryDoc.list` | 库存单据（type=inbound/outbound/transfer/count） | I07,I08,I09,I10 | `stock_entry:read` | — | 可读（L1） | 前端已声明 |
| `GET /inventory/docs/{id}` | `InventoryDoc.get` | 库存单据详情 | I07,I08,I09,I10,I14,I15 | `stock_entry:read` | — | 可读（L1） | 前端已声明 |
| `POST /inventory/docs` | `InventoryDoc.create` | 新建入库/出库/调拨/盘点单（草稿） | I07,I08,I09,I10 | `stock_entry:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /inventory/docs/{id}/post` | `InventoryDoc.post` | 过账入库/出库单（生成流水与成本层） | I07,I08 | `stock_entry:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /inventory/transfers/{id}/post` | `InventoryDoc.post` | 确认调拨（成本跟随） | I09,I14 | `stock_entry:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /inventory/counts/{id}/submit` | `StockCount.submit` | 盘点结果提交审批（盘盈亏涉及账） | I10,I15 | `stock_reconciliation:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /inventory/counts/{id}/post` | `StockCount.post` | 盘点批准后过账（只能由审批通过触发或真人） | I10,I15 | `stock_reconciliation:write` | 记 | 不可 | 前端已声明 |
| `GET /inventory/batches` | `Batch.list` | 批次与效期 | I12 | `batch:read` | — | 可读（L1） | 推断 |
| `GET /inventory/alerts` | `InventoryAlert.list` | 库存预警（低于安全库存、临期） | I11 | `stock_ledger:read` | — | 可读（L1） | 前端已声明 |
| `POST /inventory/alerts/{id}/ack` | `InventoryAlert.ack` | 预警打标/已读（白名单 L3） | I11 | `stock_ledger:read` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /inventory/replenishment/plans` | `ReplenishmentPlan.list` | 补货计划版本列表 | I19 | `material_request:read` | — | 可读（L1） | 推断 |
| `POST /inventory/replenishment/plans` | `ReplenishmentPlan.create` | 运行补货计算，生成新计划版本（只计算，不下单） | I13,I19 | `material_request:create` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /inventory/replenishment/plans/latest` | `ReplenishmentPlan.read_latest` | 最新补货计划（补货建议页） | I13 | `material_request:read` | — | 可读（L1） | 推断 |
| `GET /inventory/replenishment/plans/{id}` | `ReplenishmentPlan.get` | 计划版本详情（可用量、安全库存、交期、取整明细） | I20 | `material_request:read` | — | 可读（L1） | 推断 |
| `PATCH /inventory/replenishment/plans/{id}/lines/{lineId}` | `ReplenishmentPlan.set_lines` | 冻结/解冻计划行 | I20 | `material_request:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /inventory/replenishment/plans/{id}/lines/{lineId}/convert` | `ReplenishmentPlan.lines_convert` | 计划行转采购单草稿（source_suggestion_id 关联） | I13,I20 | `material_request:submit` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /inventory/replenishment/demand-factors` | `DemandFactor.list` | 需求因子（季节、促销） | I20 | `material_request:read` | — | 可读（L1） | 推断 |
| `POST /inventory/replenishment/demand-factors` | `DemandFactor.create` | 提议需求因子 | I20 | `material_request:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /inventory/replenishment/demand-factors/{id}/approve` | `DemandFactor.approve` | 批准需求因子（提议人不能自批） | I20 | `material_request:approve` | 记 | 仅真人 | 推断 |
| `POST /inventory/docs/{id}/reverse` | `InventoryDoc.reverse` | 红字冲回已过账库存单据（生成反向流水，原单只读） | I07,I08 | `stock_entry:cancel` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.8 采购与供应商（`proc`，32 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /procurement/lookups` | `ProcurementLookup.list` | 采购下拉数据（供应商、仓库、SKU） | I07,I08,I09,I10,L01,L04 等10页 | `purchase_order:read` | — | 可读（L1） | 前端已声明 |
| `GET /procurement/suppliers` | `Supplier.list` | 供应商 | S01 | `supplier:read` | — | 可读（L1） | 前端已声明 |
| `GET /procurement/suppliers/{id}` | `Supplier.get` | 供应商详情 | S01,S02 | `supplier:read` | — | 可读（L1） | 前端已声明 |
| `POST /procurement/suppliers` | `Supplier.create` | 新建供应商（与发起付款职责分离） | S01 | `supplier:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `PATCH /procurement/suppliers/{id}` | `Supplier.update` | 修改供应商（银行信息变更触发告警） | S01,S02 | `supplier:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /procurement/suppliers/status` | `Supplier.status` | 启用/停用供应商 | S01 | `supplier:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /procurement/rfqs` | `Rfq.list` | 询价单 | S09 | `request_for_quotation:read` | — | 可读（L1） | 推断 |
| `POST /procurement/rfqs` | `Rfq.create` | 新建询价单 | S09 | `request_for_quotation:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /procurement/rfqs/{id}` | `Rfq.get` | 询价比价详情 | S10 | `request_for_quotation:read` | — | 可读（L1） | 推断 |
| `POST /procurement/rfqs/{id}/quotes` | `Rfq.quotes` | 录入供应商报价 | S10 | `request_for_quotation:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /procurement/rfqs/{id}/award` | `Rfq.award` | 定标并生成采购单草稿 | S10 | `request_for_quotation:submit` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /procurement/contracts` | `PurchaseContract.list` | 采购合同 | S11 | `contract:read` | — | 可读（L1） | 推断 |
| `POST /procurement/contracts` | `PurchaseContract.create` | 新建采购合同 | S11 | `contract:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /procurement/contracts/{id}` | `PurchaseContract.get` | 合同详情（附件、执行进度） | S12 | `contract:read` | — | 可读（L1） | 推断 |
| `POST /procurement/contracts/{id}/submit` | `PurchaseContract.submit` | 合同提交审批 | S12 | `contract:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /procurement/supplier-scores` | `SupplierScore.list` | 供应商评估（准时率、质量、价格） | S13 | `supplier_scorecard:read` | — | 可读（L1） | 推断 |
| `POST /procurement/supplier-scores/recalculate` | `SupplierScore.recalculate` | 按规则重算评分（只读计算） | S13 | `supplier_scorecard:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /procurement/orders` | `PurchaseOrder.list` | 采购单 | S03 | `purchase_order:read` | — | 可读（L1） | 前端已声明 |
| `GET /procurement/orders/{id}` | `PurchaseOrder.get` | 采购单详情 | S05 | `purchase_order:read` | — | 可读（L1） | 前端已声明 |
| `POST /procurement/orders` | `PurchaseOrder.create` | 新建采购单（草稿） | S04 | `purchase_order:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /procurement/orders/{id}/submit` | `PurchaseOrder.submit` | 采购单提交审批 | S05 | `purchase_order:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /procurement/orders/{id}/cancel` | `PurchaseOrder.cancel` | 作废采购单 | S05 | `purchase_order:write` | 记 | 不可 | 前端已声明 |
| `GET /procurement/receipts` | `PurchaseReceipt.list` | 收货记录 | S06 | `purchase_receipt:read` | — | 可读（L1） | 前端已声明 |
| `POST /procurement/receipts` | `PurchaseReceipt.create` | 收货入库（加库存、生成暂估） | S05 | `purchase_receipt:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /procurement/returns` | `PurchaseReturn.list` | 采购退货 | S07 | `purchase_order:read` | — | 可读（L1） | 前端已声明 |
| `POST /procurement/returns` | `PurchaseReturn.create` | 新建采购退货（明细行和数量） | S07 | `purchase_order:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /procurement/returns/{id}/confirm` | `PurchaseReturn.confirm` | 确认采购退货（扣库存） | S07 | `purchase_order:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /procurement/statements` | `SupplierStatement.list` | 供应商对账单 | S08 | `supplier:read` | — | 可读（L1） | 前端已声明 |
| `POST /procurement/statements` | `SupplierStatement.create` | 生成对账单 | S08 | `supplier:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /procurement/statements/{id}/submit` | `SupplierStatement.submit` | 对账单提交审批 | S08 | `supplier:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /procurement/rfqs/{id}/send` | `Rfq.send` | 发出询价（对外发送最高 L2） | S10 | `request_for_quotation:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /procurement/statements/{id}/dispute` | `SupplierStatement.dispute` | 对供应商对账单提出异议 | S08 | `supplier:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.9 物流与头程（`logi`，17 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /logistics/shipments` | `Shipment.list` | 头程计划/运单 | L01 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `GET /logistics/shipments/{id}` | `Shipment.get` | 运单详情 | L02 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `POST /logistics/shipments` | `Shipment.create` | 新建头程运单 | L01 | `shipment:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /logistics/shipments/{id}/charges` | `Shipment.charges` | 录入头程费用（后续进到岸成本分摊） | L02 | `shipment:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /logistics/shipments/{id}/depart` | `Shipment.depart` | 发运（转在途） | L01,L02 | `shipment:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /logistics/shipments/{id}/arrive` | `Shipment.arrive` | 到仓（在途转库存） | L01,L02 | `shipment:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /logistics/carriers` | `Carrier.list` | 物流商 | L03 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `POST /logistics/carriers` | `Carrier.create` | 新建物流商 | L03 | `shipment:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /logistics/carriers/{id}` | `Carrier.update` | 修改物流商 | L03 | `shipment:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /logistics/carriers/status` | `Carrier.status` | 启用/停用物流商 | L03 | `shipment:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /logistics/rate-cards` | `RateCard.list` | 运费模板 | L04 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `POST /logistics/rate-cards` | `RateCard.create` | 新建运费模板 | L04 | `shipment:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /logistics/rate-cards/{id}` | `RateCard.update` | 修改运费模板 | L04 | `shipment:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /logistics/tracking` | `TrackingEvent.list` | 物流轨迹 | L05 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `POST /logistics/tracking/{id}/classify` | `TrackingEvent.classify` | 轨迹状态归类（白名单 L3） | L05 | `shipment:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /logistics/fee-checks` | `FreightCheck.list` | 物流费用核对 | L06 | `shipment:read` | — | 可读（L1） | 前端已声明 |
| `POST /logistics/fee-checks/{id}/submit` | `FreightCheck.submit` | 核对差异提交审批 | L06 | `shipment:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |

### 5.10 平台结算、对账与资金（`fin`，34 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /finance/imports` | `IngestBatch.list` | 文件导入批次 | F01 | `integration:read` | — | 可读（L1） | 已有 |
| `POST /finance/imports` | `IngestBatch.create` | 上传结算/订单文件并导入（异步任务，幂等：同文件哈希不重复） | F01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 已有 |
| `GET /finance/imports/{id}` | `IngestBatch.get` | 导入批次详情（行数、拒绝行、重试） | F02 | `integration:read` | — | 可读（L1） | 已有 |
| `GET /finance/rows/{table}/{id}` | `RawRecord.get` | 原始行详情（证据溯源） | F03 | `integration:read` | — | 可读（L1） | 已有 |
| `GET /finance/settlements` | `Settlement.list` | 结算与打款 | F04 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/settlements/{id}` | `Settlement.get` | 结算详情 | F05 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/settlements/{id}/split` | `Settlement.read_split` | 结算清分（清分桶、统一汇率、未确认映射） | F39 | `payment_reconciliation:read` | — | 可读（L1） | 推断 |
| `POST /finance/settlements/{id}/split/draft-voucher` | `Settlement.split_draft_voucher` | 按清分结果生成凭证草稿（映射全部确认后才可） | F39 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /finance/recon-runs` | `ReconRun.list` | 对账运行 | F06 | `report:read` | — | 可读（L1） | 已有 |
| `POST /finance/recon-runs` | `ReconRun.create` | 触发对账（确定性代码匹配，可重跑） | F06 | `integration:write` | 记 | 低风险：自动执行（L3） | 已有 |
| `GET /finance/recon-runs/{id}` | `ReconRun.get` | 对账运行详情 | F07 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/issues` | `ReconIssue.list` | 异常清单 | F08 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/issues/{id}` | `ReconIssue.get` | 异常详情 | F09 | `report:read` | — | 可读（L1） | 已有 |
| `POST /finance/issues/{id}/resolve` | `ReconIssue.resolve` | 处理对账差异（已解释/忽略；只改差异状态，不改账；原因由 AI 预填，人可直接确认） | F09 | `integration:write` | 记 | 中风险：自动执行，可撤销（L3） | 已有 |
| `POST /finance/issues/{id}/tag` | `ReconIssue.tag` | 异常自动打标签（白名单 L3） | F08 | `integration:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `POST /finance/issues/{id}/draft-voucher` | `ReconIssue.draft_voucher` | 由异常生成调整凭证草稿 | F09 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `GET /finance/profit` | `ProfitView.list` | 利润报表（管理口径） | AD04,F10 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/profit/sku/{internalSku}` | `ProfitView.read_sku` | SKU 利润详情 | F11 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/accounts` | `Account.list` | 科目表（accounts.yaml，占位编码拒绝过账） | F14 | `report:read` | — | 可读（L1） | 已有 |
| `GET /finance/fx-rates` | `FxRate.list` | 汇率表（月汇率/日汇率） | F15 | `report:read` | — | 可读（L1） | 已有 |
| `POST /finance/fx-rates` | `FxRate.create` | 新增汇率 | F15 | `integration:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `GET /finance/fee-map` | `MappingRule.list` | 费用分类映射 | F16 | `integration:read` | — | 可读（L1） | 已有 |
| `POST /finance/fee-map/{id}/confirm` | `MappingRule.confirm` | 确认费用分类 | F16 | `integration:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `GET /finance/column-maps` | `MappingRule.list` | 列映射模板 | F17 | `integration:read` | — | 可读（L1） | 已有 |
| `GET /finance/column-maps/{id}` | `MappingRule.get` | 列映射详情 | F17 | `integration:read` | — | 可读（L1） | 已有 |
| `PUT /finance/column-maps/{id}` | `MappingRule.update` | 保存列映射 | F17 | `integration:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `GET /finance/ar` | `ReceivableView.list` | 应收账款（平台应收） | F18 | `report:read` | — | 可读（L1） | 推断 |
| `GET /finance/ar/aging` | `ReceivableView.read_aging` | 应收账龄 | F18 | `report:read` | — | 可读（L1） | 推断 |
| `GET /finance/ap` | `PayableView.list` | 应付账款 | F19 | `accounts_payable:read` | — | 可读（L1） | 推断 |
| `GET /finance/ap/aging` | `PayableView.read_aging` | 应付账龄 | F19 | `accounts_payable:read` | — | 可读（L1） | 推断 |
| `GET /finance/clearing` | `Clearing.list` | 收付款核销候选 | F20 | `payment_entry:read` | — | 可读（L1） | 推断 |
| `POST /finance/clearing/submit` | `Clearing.submit` | 核销提交审批 | F20 | `approval:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /finance/cash` | `CashTransaction.list` | 资金流水 | F22 | `payment_entry:read` | — | 可读（L1） | 推断 |
| `GET /finance/exports` | `ExportPackage.list` | 导出产物（金蝶/Excel 文件与哈希） | F21 | `report:read` | — | 可读（L1） | 已有 |

### 5.11 总账与成本核算（`gl`，31 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /finance/vouchers` | `Voucher.list` | 凭证列表 | F12 | `journal_entry:read` | — | 可读（L1） | 已有 |
| `GET /finance/vouchers/{id}` | `Voucher.get` | 凭证详情（分录、来源链、审批、冲销链） | F13 | `journal_entry:read` | — | 可读（L1） | 已有 |
| `POST /finance/vouchers/{id}/submit` | `Voucher.submit` | 凭证提交审批（锁定内容哈希；AI 代提交时绑定发起人） | F13 | `journal_entry:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `POST /finance/vouchers/from-profit` | `Voucher.from_profit` | 由利润快照生成凭证草稿 | F10 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 已有 |
| `POST /finance/vouchers/from-order` | `Voucher.from_order` | 按凭证规则由订单/结算生成凭证草稿 | F12,O02 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /finance/voucher-rules` | `Voucher.list` | 凭证生成规则（逐单/按结算单/按期汇总） | F12 | `journal_entry:read` | — | 可读（L1） | 前端已声明 |
| `POST /finance/vouchers/{id}/exports` | `Voucher.exports` | 经 ledger 唯一出口导出已批准凭证（一次性令牌） | F13,F21 | `journal_entry:export` | 记 | 不可 | 已有 |
| `POST /finance/vouchers/{id}/reverse` | `Voucher.reverse` | 已过账凭证生成全额红字冲销草稿 | F13,F41 | `journal_entry:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /accounting/reversals/candidates` | `Voucher.read_candidates` | 可冲销的已过账凭证与冲销链 | F41 | `journal_entry:write` | — | 可读（L1） | 推断 |
| `GET /accounting/gl` | `LedgerView.list` | 总账/明细账 | F23 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /accounting/trial-balance` | `LedgerView.list` | 科目余额表 | F24 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /accounting/statements/{kind}` | `LedgerView.get` | 三张报表（income/balance/cashflow） | F25,F26,F27 | `report:read` | — | 可读（L1） | 前端已声明 |
| `GET /accounting/periods` | `AccountingPeriod.list` | 会计期间与结账清单 | F28 | `period_closing_voucher:read` | — | 可读（L1） | 前端已声明 |
| `POST /accounting/periods/{period}/close` | `AccountingPeriod.close` | 期末结账（检查清单全部通过；仅真人） | F28 | `period_closing_voucher:approve` | 记 | 不可 | 前端已声明 |
| `GET /accounting/period-reopen-requests` | `AccountingPeriod.list` | 反结账申请列表 | F28 | `period_closing_voucher:cancel` | — | 可读（L1） | 推断 |
| `POST /accounting/periods/{period}/reopen-requests` | `AccountingPeriod.reopen_requests` | 提交反结账申请（原因、影响），进入审批，申请人不能自批 | F28 | `period_closing_voucher:cancel` | 记 | 不可 | 推断 |
| `GET /accounting/cogs-runs` | `CogsRun.list` | 成本结转运行 | F29 | `stock_ledger:read` | — | 可读（L1） | 前端已声明 |
| `POST /accounting/cogs-runs` | `CogsRun.create` | 运行成本结转并生成结转凭证草稿 | F29 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /accounting/fx-revaluations` | `FxRevaluation.list` | 汇兑损益重估 | F32 | `exchange_rate_revaluation:read` | — | 可读（L1） | 前端已声明 |
| `POST /accounting/fx-revaluations/{id}/draft` | `FxRevaluation.draft` | 生成未实现汇兑损益凭证草稿（默认不自动冲回） | F32 | `exchange_rate_revaluation:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /accounting/landed-cost-vouchers` | `LandedCostVoucher.list` | 到岸成本分摊单 | F35 | `landed_cost_voucher:read` | — | 可读（L1） | 推断 |
| `POST /accounting/landed-cost-vouchers` | `LandedCostVoucher.create` | 由头程费用新建分摊单（按计费重分摊到批次×SKU） | F35,L02 | `landed_cost_voucher:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /accounting/landed-cost-vouchers/{id}` | `LandedCostVoucher.get` | 分摊详情（分摊明细、尾差、审计轨迹） | F36 | `landed_cost_voucher:read` | — | 可读（L1） | 推断 |
| `POST /accounting/landed-cost-vouchers/{id}/submit` | `LandedCostVoucher.submit` | 分摊单提交审批 | F36 | `landed_cost_voucher:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /accounting/grni` | `LedgerView.list` | 暂估应付余额与票到冲销进度 | F37 | `purchase_receipt:read` | — | 可读（L1） | 推断 |
| `GET /accounting/inventory-reconciliation` | `LedgerView.list` | 库存台账与 1405 库存商品/1402 在途物资科目核对 | I17 | `stock_ledger:report` | — | 可读（L1） | 推断 |
| `GET /accounting/opening` | `OpeningBatch.list` | 期初批次（科目、库存、应收应付期初） | F38 | `journal_entry:create` | — | 可读（L1） | 推断 |
| `POST /accounting/opening/imports` | `IngestBatch.create` | 导入期初数据（文件） | F38 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /accounting/opening/trial` | `OpeningBatch.trial` | 期初试算平衡（只计算） | F38 | `journal_entry:create` | 记 | 低风险：自动执行（L3） | 推断 |
| `POST /accounting/opening/activate` | `OpeningBatch.activate` | 期初启用提交审批（启用后锁定） | F38 | `journal_entry:submit` | 记 | 不可 | 推断 |
| `PATCH /finance/vouchers/{id}` | `Voucher.update` | 修改被驳回的凭证草稿（仅 draft；改后重新提交） | F13 | `journal_entry:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.12 税务（`tax`，6 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /tax/vat-returns` | `VatReturn.list` | VAT 申报跟踪（平台代扣代缴只记录不计提） | F33 | `vat_return:read` | — | 可读（L1） | 前端已声明 |
| `POST /tax/vat-returns/{id}/submit` | `VatReturn.submit` | VAT 申报记录提交审核（系统不对外申报） | F33 | `vat_return:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /tax/export-rebates` | `ExportRebateCase.list` | 出口退税/免税资料与进度 | F34 | `export_tax_rebate:read` | — | 可读（L1） | 前端已声明 |
| `POST /tax/export-rebates/{id}/documents` | `ExportRebateCase.documents` | 上传退税单证（报关单、发票） | F34 | `export_tax_rebate:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /tax/export-rebates/{id}/validate` | `ExportRebateCase.validate` | 单证齐套校验（只读检查） | F34 | `export_tax_rebate:write` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `POST /tax/export-rebates/{id}/file` | `ExportRebateCase.file` | 登记已向税务申报（只记录，不代申报） | F34 | `export_tax_rebate:submit` | 记 | 仅真人 | 推断 |

### 5.13 费用报销与预算（`exp`，24 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /expense/claims` | `ExpenseClaim.list` | 报销单（本人/部门/全部按数据范围） | EX01,ME01 | `expense_claim:read` | — | 可读（L1） | 前端已声明 |
| `POST /expense/claims` | `ExpenseClaim.create` | 新建报销单（AI 可由票据起草） | EX02 | `expense_claim:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /expense/claims/{id}` | `ExpenseClaim.get` | 报销详情 | EX03 | `expense_claim:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /expense/claims/{id}` | `ExpenseClaim.update` | 修改草稿报销单 | EX03 | `expense_claim:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /expense/claims/{id}/submit` | `ExpenseClaim.submit` | 报销提交审批（默认单级、不设金额门槛：有审批权限即可批；职责分离保留） | EX02,EX03 | `expense_claim:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /expense/claims/{id}/pay` | `ExpenseClaim.pay` | 出纳确认打款（仅审批通过后，生成凭证草稿） | EX03 | `payment_entry:submit` | 记 | 不可 | 推断 |
| `GET /expense/loans` | `EmployeeAdvance.list` | 借款单 | EX04 | `employee_advance:read` | — | 可读（L1） | 前端已声明 |
| `POST /expense/loans` | `EmployeeAdvance.create` | 新建借款单 | EX04 | `employee_advance:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /expense/loans/{id}` | `EmployeeAdvance.get` | 借款详情 | EX05 | `employee_advance:read` | — | 可读（L1） | 前端已声明 |
| `POST /expense/loans/{id}/repay` | `EmployeeAdvance.repay` | 登记还款 | EX05 | `employee_advance:write` | 记 | 不可 | 前端已声明 |
| `POST /expense/loans/{id}/offset` | `EmployeeAdvance.offset` | 借款冲抵报销 | EX05 | `employee_advance:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /expense/trips` | `TravelRequest.list` | 差旅申请 | EX06 | `travel_request:read` | — | 可读（L1） | 前端已声明 |
| `POST /expense/trips` | `TravelRequest.create` | 新建差旅申请 | EX06 | `travel_request:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /expense/trips/{id}/submit` | `TravelRequest.submit` | 差旅提交审批 | EX06 | `travel_request:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /expense/trips/{id}/match-suggestion` | `TravelRequest.match_suggestion` | AI 建议匹配报销单（只读建议） | EX06 | `travel_request:read` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `POST /expense/trips/{id}/match` | `TravelRequest.match` | 确认差旅与报销匹配 | EX06 | `travel_request:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `GET /expense/policies` | `ExpensePolicy.list` | 费用标准 | EX07 | `expense_claim_type:read` | — | 可读（L1） | 前端已声明 |
| `POST /expense/policies` | `ExpensePolicy.create` | 新建费用标准（与批报销职责分离） | EX07 | `expense_claim_type:write` | 记 | 仅真人 | 推断 |
| `PATCH /expense/policies/{id}` | `ExpensePolicy.update` | 修改费用标准 | EX07 | `expense_claim_type:write` | 记 | 仅真人 | 前端已声明 |
| `GET /budget/budgets` | `Budget.list` | 预算 | F30 | `budget:read` | — | 可读（L1） | 前端已声明 |
| `GET /budget/budgets/{id}` | `Budget.get` | 预算详情（执行占用） | F31 | `budget:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /budget/budgets/{id}` | `Budget.update` | 编制/修改预算 | F31 | `budget:write` | 记 | 不可 | 前端已声明 |
| `POST /budget/budgets/{id}/adjustments` | `Budget.adjustments` | 预算调整申请（进审批） | F31 | `budget:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /expense/loans/{id}/pay` | `EmployeeAdvance.pay` | 借款付款（生成付款凭证草稿，走审批） | EX05 | `employee_advance:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.14 广告（`ads`，6 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /ads/campaigns` | `AdCampaign.list` | 广告活动 | AD01,AD04 | `advertisement:read` | — | 可读（L1） | 推断 |
| `GET /ads/imports` | `IngestBatch.list` | 广告花费导入批次 | AD02 | `advertisement:read` | — | 可读（L1） | 推断 |
| `POST /ads/imports` | `IngestBatch.create` | 导入广告花费报表 | AD02 | `advertisement:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /ads/performance` | `AdPerformance.list` | 广告效果（ACoS、ROAS） | AD03 | `advertisement:read` | — | 可读（L1） | 推断 |
| `GET /ads/allocations` | `AdAllocation.list` | 广告费分摊结果 | AD04 | `advertisement:read` | — | 可读（L1） | 推断 |
| `PUT /ads/campaigns/{id}/allocation` | `AdCampaign.set_allocation` | 保存分摊比例（影响管理利润） | AD04 | `advertisement:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.15 CRM 与客服（`crm`，24 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /crm/dashboard` | `CrmDashboard.list` | CRM 看板 | R01 | `customer:read` | — | 可读（L1） | 前端已声明 |
| `GET /crm/accounts` | `Customer.list` | 客户 | R02,R12 | `customer:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/accounts` | `Customer.create` | 新建客户 | R02 | `customer:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /crm/accounts/{id}` | `Customer.get` | 客户详情 | R03 | `customer:read` | — | 可读（L1） | 前端已声明 |
| `GET /crm/leads` | `Lead.list` | 线索 | R04,R05 | `lead:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/leads` | `Lead.create` | 新建线索 | R04 | `lead:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /crm/leads/{id}` | `Lead.get` | 线索详情 | R06 | `lead:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /crm/leads/{id}/stage` | `Lead.set_stage` | 改线索阶段（看板拖拽） | R05 | `lead:write` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `POST /crm/leads/{id}/convert` | `Lead.convert` | 线索转客户/商机 | R06 | `lead:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /crm/opportunities` | `Opportunity.list` | 商机 | R07 | `lead:read` | — | 可读（L1） | 前端已声明 |
| `GET /crm/opportunities/{id}` | `Opportunity.get` | 商机详情 | R08 | `lead:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/opportunities/{id}/win` | `Opportunity.win` | 赢单并生成销售订单草稿（修复断点 1） | R08 | `customer:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /crm/contacts` | `Contact.list` | 联系人（联系方式按字段权限脱敏） | R09 | `contact:read` | — | 可读（L1） | 前端已声明 |
| `GET /crm/contacts/{id}` | `Contact.get` | 联系人详情 | R10 | `contact:read` | — | 可读（L1） | 前端已声明 |
| `GET /crm/activities` | `Activity.list` | 跟进日历 | R11 | `contact:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/activities` | `Activity.create` | 新建跟进提醒（白名单 L3） | R11 | `customer:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /crm/tickets` | `Ticket.list` | 售后工单 | R12 | `ticket:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/tickets` | `Ticket.create` | 新建工单（内部，L3 可自动分类建单） | R12 | `ticket:create` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `GET /crm/tickets/{id}` | `Ticket.get` | 工单详情 | R13 | `ticket:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /crm/tickets/{id}/status` | `Ticket.set_status` | 改工单状态/分类 | R13 | `ticket:write` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `POST /crm/tickets/{id}/replies` | `Ticket.replies` | 对外回复买家（对外发送最高 L2） | R13 | `ticket:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /crm/reviews` | `CustomerReview.list` | 评价 | R14 | `ticket:read` | — | 可读（L1） | 前端已声明 |
| `POST /crm/accounts/{id}/deactivate` | `Customer.deactivate` | 停用客户（不删除） | R03 | `customer:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /crm/opportunities/{id}/lose` | `Opportunity.lose` | 商机输单（写原因） | R08 | `customer:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |

### 5.16 审批中心（`wf`，9 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /approvals` | `Approval.list` | 审批列表（scope=todo/submitted/cc/agent/all） | F13,W01,W02,W05,W06 | `approval:read` | — | 可读（L1） | 已有 |
| `GET /approvals/{id}` | `Approval.get` | 审批详情（内容哈希、证据、链路） | W03 | `approval:read` | — | 可读（L1） | 已有 |
| `POST /approvals/{id}/decide` | `Approval.decide` | 批准/驳回（唯一决定入口；校验内容哈希、职责分离、轮次；不能审批自己提交或 AI 代自己提交的单） | EX03,F13,F28,F36,HR09,I20 等10页 | `approval:approve` | 记 | 仅真人 | 已有 |
| `POST /approvals/{id}/withdraw` | `Approval.withdraw` | 提交人撤回待审批单 | W02 | `approval:create` | 记 | 不可 | 推断 |
| `POST /approvals/{id}/initiator-confirm` | `Approval.initiator_confirm` | 发起人本人确认（AI 发起的高风险或钱账动作解析不到可用审批人时，退回发起人本人确认后才生效；留痕「无审批人，发起人确认」） | W02,W03,W05 | `approval:create` | 记 | 仅真人 | 推断 |
| `GET /workflow/rules/resolve` | `WorkflowRule.read_resolve` | 提交前预览审批人（返回将由谁审批，或「无审批人，提交即生效」/「需你本人确认」） | W02,W03,W04 | `approval:read` | — | 可读（L1） | 推断 |
| `GET /approvals/types` | `ApprovalType.list` | 审批类型注册表 | W04,W07 | `approval:read` | — | 可读（L1） | 前端已声明 |
| `GET /workflow/rules` | `WorkflowRule.list` | 审批规则（审批人从流程配置解析；配置了就必须审，法人/老大也一样；没配置或解析不到可用账号则免审直接生效并留痕；AI 发起的高风险/钱账动作无审批人时退回发起人本人确认） | W04,W07 | `approval:read` | — | 可读（L1） | 前端已声明 |
| `PUT /workflow/rules/{id}` | `WorkflowRule.update` | 保存审批规则 | W04,W07 | `approval:write` | 记 | 仅真人 | 前端已声明 |

### 5.17 通知与 IM 插件（`notify`，20 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /notify/messages` | `Notification.list` | 站内消息（合并原 /notifications） | N01,N03 | `notification:read` | — | 可读（L1） | 前端已声明 |
| `POST /notify/messages/{id}/read` | `Notification.read` | 标记已读 | N01,N03 | `notification:read` | — | 低风险：自动执行（L3） | 前端已声明 |
| `POST /notify/messages/read-all` | `Notification.read_all` | 全部已读 | N01,N03 | `notification:read` | — | 低风险：自动执行（L3） | 推断 |
| `GET /notify/subscriptions` | `Subscription.list` | 我的订阅 | N02 | `notification:read` | — | 可读（L1） | 前端已声明 |
| `PUT /notify/subscriptions` | `Subscription.update` | 保存订阅 | N02 | `notification:write` | 记 | 不可 | 前端已声明 |
| `GET /notify/rules` | `NotifyRule.list` | 通知规则（原 /admin/notifications） | SYS09 | `notification:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /notify/rules/{id}` | `NotifyRule.update` | 修改通知规则 | SYS09 | `notification:write` | 记 | 仅真人 | 前端已声明 |
| `GET /notify/channel-plugins` | `ChannelPlugin.list` | 可用渠道插件及能力（send/卡片/绑定/回调） | SYS25,SYS26 | `notification:read` | — | 可读（L1） | 推断 |
| `GET /notify/channels` | `NotifyChannel.list` | 已配置通知渠道（密钥只显示“已配置”） | SYS25 | `notification:read` | — | 可读（L1） | 前端已声明 |
| `POST /notify/channels` | `NotifyChannel.create` | 新增渠道（飞书/企微/钉钉/邮件/Webhook） | SYS26 | `notification:create` | 记 | 仅真人 | 推断 |
| `PATCH /notify/channels/{id}` | `NotifyChannel.update` | 启用/停用/修改渠道 | SYS25 | `notification:write` | 记 | 仅真人 | 推断 |
| `POST /notify/channels/{id}/test` | `NotifyChannel.test` | 测试连通 | SYS25,SYS26 | `notification:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /im/bindings/me` | `ImBinding.read_me` | 我的 IM 绑定 | SYS19 | `integration:read` | — | 可读（L1） | 推断 |
| `POST /im/bindings/{channel}/start` | `ImBinding.start` | 发起 IM 账号绑定（跳转官方授权） | SYS19 | `integration:read` | 记 | 不可 | 推断 |
| `GET /im/bindings/{channel}/oauth-callback` | `ImBinding.read_oauth_callback` | IM 授权回调，完成绑定（state 防伪） | SYS19 | `public` | 记 | 不可 | 推断 |
| `DELETE /im/bindings/{channel}` | `ImBinding.delete` | 解绑 IM 账号 | SYS19 | `integration:read` | 记 | 不可 | 推断 |
| `GET /im/approval-settings` | `ImApprovalSetting.list` | IM 审批设置（后期启用：可批类型、卡片有效期；首期审批只在平台内） | SYS20 | `approval:write` | — | 可读（L1） | 推断 |
| `PUT /im/approval-settings` | `ImApprovalSetting.update` | 保存 IM 审批设置 | SYS20 | `approval:write` | 记 | 仅真人 | 推断 |
| `GET /im/approval-cards/{approvalId}/preview` | `ImApprovalCard.read_preview` | 预览某审批的 IM 卡片 | W08 | `approval:approve` | — | 可读（L1） | 推断 |
| `POST /im/callbacks/{channel}` | `ImApprovalCard.invoke` | IM 卡片按钮回调（签名、防重放、绑定、内容哈希、权限复核后调用统一审批） | W08 | `signature` | 记 | 不可 | 推断 |

### 5.18 人事与薪资（`hr`，24 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /hr/departments` | `Department.list` | 组织架构/部门树 | HR01 | `employee_record:read` | — | 可读（L1） | 前端已声明 |
| `POST /hr/departments` | `Department.create` | 新建/调整部门 | HR01 | `employee_record:write` | 记 | 不可 | 推断 |
| `GET /hr/employees` | `Employee.list` | 员工档案（证件、薪资字段受字段权限） | HR02,ME01 | `employee_record:read` | — | 可读（L1） | 推断 |
| `POST /hr/employees` | `Employee.create` | 新建员工 | HR02,HR04 | `employee_record:write` | 记 | 不可 | 推断 |
| `GET /hr/employees/{id}` | `Employee.get` | 员工详情 | HR03 | `employee_record:read` | 敏感读也记 | 可读（L1） | 推断 |
| `PATCH /hr/employees/{id}` | `Employee.update` | 修改员工 | HR03 | `employee_record:write` | 记 | 不可 | 推断 |
| `POST /hr/employees/{id}/status` | `Employee.status` | 入职/转正/离职（离职触发停用账号、解绑 IM、回收资产） | HR03,HR04 | `employee_record:write` | 记 | 不可 | 推断 |
| `GET /hr/attendance` | `AttendanceRecord.list` | 考勤记录 | HR05 | `attendance:read` | — | 可读（L1） | 推断 |
| `POST /hr/attendance/imports` | `IngestBatch.create` | 导入考勤 | HR05 | `attendance:write` | 记 | 不可 | 推断 |
| `GET /hr/leave-requests` | `LeaveRequest.list` | 请假单 | HR06 | `leave_application:read` | — | 可读（L1） | 推断 |
| `POST /hr/leave-requests` | `LeaveRequest.create` | 提交请假（进审批） | HR06 | `leave_application:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /hr/payroll-runs` | `PayrollRun.list` | 薪资批次列表（只读；AI 按被代表人权限可读，字段策略照常脱敏） | HR07 | `salary_slip:read` | 敏感读也记 | 可读（L1） | 推断 |
| `POST /hr/payroll-runs/calculate` | `PayrollRun.calculate` | 发起算薪（规则引擎确定性计算，记录规则版本与输入哈希；异步） | HR07 | `salary_slip:create` | 记 | 不可 | 前端已声明 |
| `GET /hr/payroll-runs/{id}` | `PayrollRun.get` | 薪资批次详情 | HR08 | `salary_slip:read` | 敏感读也记 | 可读（L1） | 前端已声明 |
| `POST /hr/payroll-runs/{id}/review` | `PayrollRun.review` | HR 复核（调整须填原因并重算） | HR09 | `salary_slip:review` | 记 | 不可 | 前端已声明 |
| `POST /hr/payroll-runs/{id}/submit` | `PayrollRun.submit` | 复核后提交审批（发起人/复核人不能审批） | HR09 | `salary_slip:submit` | 记 | 不可 | 推断 |
| `POST /hr/payroll-runs/{id}/publish-payslips` | `PayrollRun.publish_payslips` | 批准后发布工资条并生成工资凭证草稿 | HR08 | `salary_slip:approve` | 记 | 不可 | 推断 |
| `GET /hr/payroll-rules` | `PayrollRule.list` | 社保公积金与个税规则版本（未核实版本不能正式算薪） | HR10 | `salary_structure:read` | — | 可读（L1） | 前端已声明 |
| `POST /hr/payroll-rules` | `PayrollRule.create` | 新建规则版本 | HR10 | `salary_structure:write` | 记 | 不可 | 推断 |
| `POST /hr/payroll-rules/{id}/verify` | `PayrollRule.verify` | HR/财务标记规则为已核实 | HR10 | `salary_structure:approve` | 记 | 不可 | 推断 |
| `GET /hr/tax-deductions` | `TaxDeduction.list` | 专项附加扣除 | HR11 | `employee_tax_exemption_declaration:read` | 敏感读也记 | 可读（L1） | 推断 |
| `POST /hr/tax-deductions` | `TaxDeduction.create` | 登记专项附加扣除 | HR11 | `employee_tax_exemption_declaration:write` | 记 | 不可 | 推断 |
| `GET /hr/payslips/mine` | `Payslip.read_mine` | 我的工资条（只看本人） | HR12 | `salary_slip:read_own` | 敏感读也记 | 可读（L1） | 推断 |
| `POST /hr/departments/{id}/deactivate` | `Department.deactivate` | 停用部门（需先迁出人员） | HR01 | `employee_record:write` | 记 | 仅真人 | 推断 |

### 5.19 行政（`office`，15 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /office/contracts` | `OfficeContract.list` | 合同管理 | AM01 | `contract:read` | — | 可读（L1） | 推断 |
| `POST /office/contracts` | `OfficeContract.create` | 新建合同 | AM01 | `contract:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `PATCH /office/contracts/{id}` | `OfficeContract.update` | 修改合同（到期提醒 L3） | AM01 | `contract:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /office/assets` | `Asset.list` | 固定资产 | AM02 | `asset:read` | — | 可读（L1） | 推断 |
| `POST /office/assets` | `Asset.create` | 新增资产 | AM02 | `asset:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /office/assets/{id}` | `Asset.get` | 资产详情（领用、折旧） | AM03 | `asset:read` | — | 可读（L1） | 推断 |
| `POST /office/assets/{id}/checkout` | `Asset.checkout` | 资产领用 | AM03 | `asset:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /office/assets/{id}/return` | `Asset.return` | 资产归还 | AM03 | `asset:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /office/assets/depreciation-runs` | `DepreciationRun.create` | 计提折旧并生成凭证草稿 | AM02 | `journal_entry:create` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /office/announcements` | `Announcement.list` | 公告 | AM04 | `notification:read` | — | 可读（L1） | 推断 |
| `POST /office/announcements` | `Announcement.create` | 新建公告草稿 | AM04 | `notification:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /office/announcements/{id}/publish` | `Announcement.publish` | 发布公告（真人） | AM04 | `notification:write` | 记 | 不可 | 推断 |
| `GET /office/supplies` | `OfficeSupply.list` | 办公用品库存 | AM05 | `office_supply:read` | — | 可读（L1） | 推断 |
| `POST /office/supply-requests` | `SupplyRequest.create` | 领用申请 | AM05 | `office_supply:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /office/assets/{id}/dispose` | `Asset.dispose` | 资产处置申请（生成处置凭证草稿，走审批） | AM03 | `asset:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |

### 5.20 知识库与新人上手（`kb`，35 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /kb/spaces` | `KbSpace.list` | 知识空间（含智能体绑定的知识库） | G10,K01 | `document:read` | — | 可读（L1） | 前端已声明 |
| `GET /kb/spaces/{id}` | `KbSpace.get` | 空间详情 | G11,K03 | `document:read` | — | 可读（L1） | 前端已声明 |
| `PUT /kb/spaces/{id}/acl` | `KbSpace.set_acl` | 空间可见/编辑/下载权限 | K03 | `document:write` | 记 | 仅真人 | 前端已声明 |
| `PUT /kb/spaces/{id}/members` | `KbSpace.set_members` | 空间成员 | K03 | `document:write` | 记 | 仅真人 | 前端已声明 |
| `POST /kb/spaces/{id}/folders` | `KbSpace.folders` | 新建文件夹 | K03 | `document:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `PATCH /kb/folders/{id}` | `KbSpace.update` | 重命名文件夹 | K03 | `document:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /kb/docs` | `KnowledgePage.list` | 文档列表（按有效权限过滤） | G11,K01,K03 | `document:read` | — | 可读（L1） | 前端已声明 |
| `POST /kb/docs` | `KnowledgePage.create` | 新建文档草稿 | K04 | `document:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /kb/docs/{id}` | `KnowledgePage.get` | 文档详情（敏感文档记访问日志） | K02 | `document:read` | 敏感读也记 | 可读（L1） | 前端已声明 |
| `GET /kb/docs/{id}/versions` | `KnowledgePage.read_versions` | 版本历史 | K02,K04 | `document:read` | — | 可读（L1） | 前端已声明 |
| `POST /kb/docs/{id}/versions` | `KnowledgePage.versions` | 保存新版本 | K04 | `document:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /kb/docs/{id}/submit` | `KnowledgePage.submit` | 提交发布审核 | K04 | `document:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 前端已声明 |
| `POST /kb/docs/{id}/archive` | `KnowledgePage.archive` | 撤回/归档文档 | K02 | `document:write` | 记 | 不可 | 前端已声明 |
| `POST /kb/docs/{id}/attachments` | `KnowledgePage.attachments` | 上传附件 | K04 | `document:write` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /kb/reviews` | `KnowledgePage.list` | 待发布审核 | K05 | `document:approve` | — | 可读（L1） | 前端已声明 |
| `POST /kb/reviews/{id}/decide` | `KnowledgePage.decide` | 审核发布/驳回 | K05 | `document:approve` | 记 | 仅真人 | 前端已声明 |
| `GET /kb/search` | `KbIndex.list` | 检索（关键词+段落，按权限过滤，带引用） | K01,K08 | `document:read` | — | 可读（L1） | 前端已声明 |
| `GET /kb/qa` | `KnowledgeQa.list` | 沉淀问答与经验 | K06 | `document:read` | — | 可读（L1） | 前端已声明 |
| `POST /kb/qa/suggest` | `KnowledgeQa.suggest` | AI 由已解决工单提炼问答草稿（进审核） | K06 | `document:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `GET /kb/expiring` | `KbIndex.list` | 即将到期文档、合同、证书 | K07 | `document:read` | — | 可读（L1） | 前端已声明 |
| `POST /kb/index/rebuild` | `KbIndex.rebuild` | 重建检索索引（异步） | K08 | `document:write` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `GET /kb/personal/{employeeId}` | `PersonalFile.get` | 员工个人档案（本人与人事） | HR13 | `employee_record:read` | 敏感读也记 | 可读（L1） | 前端已声明 |
| `POST /kb/personal/{employeeId}/files` | `PersonalFile.files` | 上传个人档案文件 | HR13 | `employee_record:write` | 记 | 不可 | 前端已声明 |
| `POST /kb/personal/{employeeId}/files/{id}/download` | `PersonalFile.files_download` | 下载个人档案（敏感，记日志） | HR13 | `employee_record:read` | 敏感读也记 | 不可 | 前端已声明 |
| `GET /onboarding/me` | `OnboardingChecklist.read_me` | 我的上手清单 | ON01 | `document:read` | — | 可读（L1） | 前端已声明 |
| `PUT /onboarding/checklists/{id}` | `OnboardingChecklist.set_checklists` | 维护分角色上手清单与页面引导 | ON02 | `document:write` | 记 | 不可 | 前端已声明 |
| `POST /onboarding/ask` | `OnboardingChecklist.ask` | 上手问答（只读，给“带我去做”链接） | ON01 | `document:read` | — | 可读（L1） | 前端已声明 |
| `GET /kb/docs/{id}/sources` | `KnowledgePage.read_sources` | 知识页引用来源（原件、业务实体、问答；不可见来源只显示“无权查看”） | K02 | `document:read` | — | 可读（L1） | 推断 |
| `POST /kb/compile-runs` | `KbCompileRun.create` | AI 增量整理：新资料或实体事件触发更新知识页草稿（覆盖所有空间；只读取发起者或管理员有权看的来源，产出继承原空间权限，不跨空间） | G11,K08 | `document:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /kb/compile-runs/{id}` | `KbCompileRun.get` | 编译运行详情：读了哪些来源、改了哪些页、生成哪些审核项 | K08 | `document:read` | — | 可读（L1） | 推断 |
| `GET /kb/lint-findings` | `KbLintFinding.list` | 知识体检：孤立页、断链、矛盾、过期、与实体数据不一致 | K05,K07 | `document:read` | — | 可读（L1） | 推断 |
| `POST /kb/lint-runs` | `KbLintFinding.create` | 发起知识体检（结构检查 + AI 语义检查） | K05 | `document:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /kb/entity-pages/{type}/{id}` | `KnowledgePage.get` | 业务实体的知识页（规则、经验、历史问题；先校验实体读权限再校验知识权限） | K02,P02 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /kb/graph` | `KbIndex.list` | 知识关联图（只含调用人可见的页和实体） | K01 | `document:read` | — | 可读（L1） | 推断 |
| `POST /kb/lint-findings/{id}/dismiss` | `KbLintFinding.dismiss` | 忽略体检问题（写原因，可恢复） | K05 | `document:write` | 记 | 低风险：自动执行（L3） | 推断 |

### 5.21 平台集成（`integ`，13 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /integrations/connectors` | `Connector.list` | 已注册连接器（Amazon 结算 V2、Shopify 打款、通用映射） | INT01,SYS06 | `integration:read` | — | 可读（L1） | 已有 |
| `GET /integrations/platform-auths` | `PlatformAuth.list` | 平台授权状态（只显示连接状态和脱敏信息） | SYS06 | `integration:read` | — | 可读（L1） | 前端已声明 |
| `POST /integrations/platform-auths/{platform}/connect` | `PlatformAuth.connect` | 发起平台授权（SP-API/Shopify/领星，密钥只存服务端） | SYS06 | `integration:write` | 记 | 仅真人 | 推断 |
| `DELETE /integrations/platform-auths/{platform}` | `PlatformAuth.delete` | 断开平台授权 | SYS06 | `integration:write` | 记 | 仅真人 | 推断 |
| `POST /integrations/imports` | `IngestBatch.create` | 导入向导：上传领星/赛狐导出并识别格式 | INT01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /integrations/imports/{id}/preview` | `IngestBatch.preview` | 导入预览（映射、拒绝行） | INT01 | `integration:import` | — | 低风险：自动执行（L3） | 推断 |
| `POST /integrations/imports/{id}/confirm` | `IngestBatch.confirm` | 确认导入（写入业务表，幂等） | INT01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /integrations/sync-jobs` | `SyncJob.list` | 平台同步任务 | INT02 | `integration:read` | — | 可读（L1） | 推断 |
| `POST /integrations/sync-jobs` | `SyncJob.create` | 启动一次只读拉取（结算报告、订单、打款） | INT02 | `integration:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /integrations/ledger-targets/{target}` | `LedgerTarget.get` | 账套导出目标设置（顺序：kingdee 金蝶 → yonyou 用友 → 其他如 erpnext） | INT03,INT04 | `integration:read` | — | 可读（L1） | 推断 |
| `PUT /integrations/ledger-targets/{target}` | `LedgerTarget.update` | 保存账套导出设置 | INT03,INT04 | `integration:write` | 记 | 仅真人 | 推断 |
| `POST /integrations/ledger-targets/{target}/test` | `LedgerTarget.test` | 测试账套连通（金蝶/用友；其他目标可选） | INT04 | `integration:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /integrations/logs` | `IntegrationLog.list` | 集成日志 | INT05 | `integration:read` | — | 可读（L1） | 推断 |

### 5.22 智能体中心（`agent`，55 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /agent/mode` | `AgentMode.list` | AI 运行状态（正常/降级/关闭） | G19 | `authenticated` | — | 可读（L1） | 推断 |
| `PUT /agent/mode` | `AgentMode.update` | 切换 AI 总开关（恢复正常只能真人） | G19 | `agent_tool:write` | 记 | 仅真人 | 前端已声明 |
| `GET /agent/definitions` | `AgentDefinition.list` | 智能体档案 | G02,G03 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/definitions` | `AgentDefinition.create` | 新建智能体档案（模型、提示词、知识库、工具、范围收窄） | G02 | `agent_tool:create` | 记 | 仅真人 | 推断 |
| `GET /agent/definitions/{id}` | `AgentDefinition.get` | 智能体详情 | G03 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `PATCH /agent/definitions/{id}` | `AgentDefinition.update` | 修改智能体档案 | G03 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `PUT /agent/definitions/{id}/tools` | `AgentDefinition.set_tools` | 设置智能体可用工具（只能收窄） | G03,G04 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `GET /agent/threads` | `AgentThread.list` | 会话列表（只看本人会话） | G01,G05 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/threads` | `AgentThread.create` | 新建会话 | G01 | `system:read` | 记 | 可读（L1） | 推断 |
| `GET /agent/threads/{id}/messages` | `AgentThread.read_messages` | 会话消息 | G01,G05 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `POST /agent/threads/{id}/messages` | `AgentThread.messages` | 发送消息（SSE 流式；快照发起人 userId+role，返回时复核） | G01 | `system:read` | 记 | 可读（L1） | 已有 |
| `GET /agent/runs` | `AgentRun.list` | 运行记录 | G02,G08 | `agent_tool:read` | — | 可读（L1） | 已有 |
| `POST /agent/runs` | `AgentRun.create` | 登记一次提问运行（绑定发起人） | G01 | `system:read` | 记 | 可读（L1） | 前端已声明 |
| `GET /agent/runs/{id}` | `AgentRun.get` | 运行详情 | G09 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `GET /agent/runs/{id}/steps` | `AgentRun.read_steps` | 运行步骤与工具调用 | G07,G09 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/runs/{id}/suggestion-step` | `AgentRun.suggestion_step` | 记录建议步骤（证据、把握度） | G01 | `system:read` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /agent/runs/{id}/cancel` | `AgentRun.cancel` | 停止进行中的运行（用户点「停止」；登出/切换账号时服务端自动停止，无需前端调用） | G01 | `authenticated` | 记 | 不可 | 推断 |
| `GET /agent/suggestions` | `AgentSuggestion.list` | 智能体建议（生命周期） | G01,W05 | `agent_suggestion:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/suggestions` | `AgentSuggestion.create` | 提交建议→生成 origin=agent 草稿并进审批中心（不审批、不写账） | G01,I11 | `agent_suggestion:create` | 记 | 中风险：自动执行，可撤销（L3） | 前端已声明 |
| `POST /agent/suggestions/{id}/undo` | `AgentSuggestion.undo` | 撤销 24 小时内 AI 自动执行的低/中风险动作 | G21,W05 | `agent_suggestion:create` | 记 | 不可 | 推断 |
| `POST /agent/suggestions/{id}/dismiss` | `AgentSuggestion.dismiss` | 忽略 L1 建议 | G21,W05 | `agent_suggestion:read` | 记 | 不可 | 推断 |
| `GET /agent/tasks` | `AgentTask.list` | 定时/后台任务 | G06 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/tasks` | `AgentTask.create` | 新建定时任务（指定委托人） | G06 | `agent_tool:create` | 记 | 仅真人 | 推断 |
| `GET /agent/tasks/{id}` | `AgentTask.get` | 任务详情 | G07 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /agent/tasks/{id}` | `AgentTask.update` | 启停/修改任务 | G07 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `GET /agent/prompts` | `PromptVersion.list` | 提示词版本 | G12 | `agent_tool:read` | — | 可读（L1） | 已有 |
| `POST /agent/prompts` | `PromptVersion.create` | 新建提示词版本 | G12 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `GET /agent/evals` | `EvalRun.list` | 评测运行 | G13 | `agent_tool:read` | — | 可读（L1） | 已有 |
| `POST /agent/evals` | `EvalRun.create` | 发起评测（异步） | G13 | `agent_tool:write` | 记 | 低风险：自动执行（L3） | 已有 |
| `GET /agent/evals/{id}/cases` | `EvalRun.read_cases` | 评测用例结果 | G14 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `GET /agent/usage/calls` | `LlmCall.list` | LLM 调用记录 | G15 | `agent_tool:read` | — | 可读（L1） | 已有 |
| `GET /agent/usage/calls/{id}` | `LlmCall.get` | 调用详情（提示词全文按保留期） | G16 | `agent_tool:read` | 敏感读也记 | 可读（L1） | 已有 |
| `GET /agent/usage/summary` | `LlmUsage.list` | 用量与预算汇总 | G15 | `agent_tool:read` | — | 可读（L1） | 已有 |
| `PUT /agent/budgets` | `AgentBudget.update` | 设置 LLM 预算与告警阈值 | G15 | `agent_tool:write` | 记 | 仅真人 | 已有 |
| `GET /agent/tools` | `AgentTool.list` | 工具注册表（ERP/联网/MCP/HTTP） | G04 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `POST /agent/tools` | `AgentTool.create` | 新增工具（联网检索、自定义 HTTP；密钥只存服务端） | G25 | `agent_tool:create` | 记 | 仅真人 | 前端已声明 |
| `GET /agent/tools/{id}` | `AgentTool.get` | 工具详情与配置 | G24 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `PATCH /agent/tools/{id}` | `AgentTool.update` | 启停、可用角色、频率上限、side_effect、自主等级上限 | G04,G24 | `agent_tool:write` | 记 | 仅真人 | 前端已声明 |
| `POST /agent/tools/{id}/test` | `AgentTool.test` | 测试调用工具（不改数据） | G24 | `agent_tool:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /agent/mcp-servers` | `McpServer.list` | MCP 服务器 | G26 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `POST /agent/mcp-servers` | `McpServer.create` | 登记外部 MCP 服务器 | G26 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `POST /agent/mcp-servers/{id}/import` | `McpServer.import` | 发现并导入工具（默认停用） | G26 | `agent_tool:write` | 记 | 仅真人 | 前端已声明 |
| `GET /agent/autonomy-policies` | `AutonomyPolicy.list` | 自主等级与风险分级策略（模块×动作×角色；只能收窄，不能放宽硬上限） | G18 | `agent_tool:read` | — | 可读（L1） | 前端已声明 |
| `PATCH /agent/autonomy-policies/{id}` | `AutonomyPolicy.update` | 调整自主等级（服务端按硬上限降级） | G18 | `agent_tool:write` | 记 | 仅真人 | 前端已声明 |
| `GET /agent/inbox` | `AgentInbox.list` | 票据收件箱 | G20 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `POST /agent/inbox` | `AgentInbox.create` | 上传票据（自动分类 L3，起草报销 L2） | G20 | `agent_tool:read` | 记 | 低风险：自动执行（L3） | 前端已声明 |
| `GET /agent/alerts` | `AgentAlert.list` | 主动提醒 | G21 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `POST /agent/alerts/{id}/ack` | `AgentAlert.ack` | 提醒已读/稍后 | G21 | `agent_tool:read` | — | 低风险：自动执行（L3） | 推断 |
| `GET /agent/trust` | `AgentTrust.list` | 可信度看板（采纳率、撤销率、评测分） | G22 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `GET /agent/scope-narrowing` | `ScopeNarrowing.list` | AI 范围收窄规则 | G23 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `PUT /agent/scope-narrowing` | `ScopeNarrowing.update` | 保存范围收窄（只能收窄） | G23 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `GET /agent/model-config` | `ModelConfig.list` | 模型设置（OpenAI 兼容：baseUrl、model；只返回 hasApiKey，api_key 永不回显） | G17 | `agent_tool:read` | — | 可读（L1） | 推断 |
| `PUT /agent/model-config` | `ModelConfig.update` | 保存模型设置（baseUrl、model、apiKey 只写；加密存储，不回显、不进日志；保存后 agent worker 自动重载） | G17 | `agent_tool:write` | 记 | 仅真人 | 推断 |
| `POST /agent/model-config/test` | `ModelConfig.test` | 测试模型连通（用一句固定提示调用一次；返回成功/失败原因，不回显密钥） | G17 | `agent_tool:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /agent/delegations` | `Delegation.list` | 委托通行证记录（系统自动签发/续期/作废；管理员审计用，普通用户看不到也无需操作） | G17 | `audit_log:read` | — | 可读（L1） | 推断 |

### 5.23 本体与实体目录（`onto`，8 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /ontology/entity-types` | `EntityType.list` | 实体类型目录（属性、关系、状态机；按调用人可见字段裁剪） | G04,SYS03 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /ontology/entity-types/{type}` | `EntityType.get` | 单个实体类型定义（含允许动作与所需权限点） | G04,G24 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /ontology/actions` | `ActionType.list` | 当前调用人可执行的实体动作清单（agent 工具目录的唯一来源） | G04,G24 | `authenticated` | — | 可读（L1） | 推断 |
| `POST /ontology/actions/{actionId}/dry-run` | `ActionType.dry_run` | 动作预检：校验参数、权限、状态机、职责分离与自主等级，不写入 | G01,G24 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /ontology/event-types` | `EventType.list` | 实体事件类型与订阅者（调度器、通知、孪生、知识编译） | G06 | `system:read` | — | 可读（L1） | 推断 |
| `GET /entities/{type}/{id}/versions` | `EntityVersion.list` | 实体版本历史（谁、何时、经哪个动作或导入批次改变；按实体读权限） | F02,U01 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /entities/{type}/{id}/versions/{version}` | `EntityVersion.get` | 实体某版本快照（字段级差异） | F02,U01 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /entities/{type}/{id}/lineage` | `EntityVersion.read_lineage` | 溯源：原始文件/行 → 清洗规则 → 映射版本 → 实体 → 凭证 | F02,F05,U01 | `authenticated` | 敏感读也记 | 可读（L1） | 推断 |

### 5.24 数据进入与溯源（`ingest`，12 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /ingest/batches` | `IngestBatch.list` | 统一导入批次（结算、订单、广告、考勤、期初、平台同步共用一条链路） | AD02,F01,INT01,INT02,INT05 | `integration:read` | — | 可读（L1） | 推断 |
| `GET /ingest/batches/{id}` | `IngestBatch.get` | 批次详情：原件哈希、行数、各阶段计数（落地/清洗/去重/映射/投射） | F02,INT01 | `integration:read` | — | 可读（L1） | 推断 |
| `GET /ingest/batches/{id}/raw-records` | `RawRecord.list` | 原始记录（不可变原件，只读；敏感字段按字段权限脱敏） | F02,INT01 | `integration:read` | 敏感读也记 | 可读（L1） | 推断 |
| `GET /ingest/batches/{id}/issues` | `CleansingIssue.list` | 清洗问题：校验失败、疑似重复、映射缺失、口径冲突 | F02,INT01 | `integration:read` | — | 可读（L1） | 推断 |
| `POST /ingest/batches/{id}/issues/{issueId}/resolve` | `CleansingIssue.resolve` | 处理清洗问题（agent 优先自动处理：补映射/判定重复/忽略并说明原因；涉及钱和账的结论降为人工确认） | F02,INT01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /ingest/batches/{id}/project` | `IngestBatch.project` | 把通过清洗的记录投射为实体（幂等；钱和账相关实体只生成草稿） | F02,INT01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /ingest/batches/{id}/supersede` | `IngestBatch.supersede` | 用新批次替代旧批次（不删除，旧投射通过补偿事件冲回） | F02 | `integration:import` | 记 | 仅真人 | 推断 |
| `GET /ingest/mapping-rules` | `MappingRule.list` | 映射规则库（列映射、费用分类、SKU 映射、单位与币种换算的统一视图，带版本） | F16,F17,P08 | `integration:read` | — | 可读（L1） | 推断 |
| `PUT /ingest/mapping-rules/{id}` | `MappingRule.update` | 保存映射规则新版本（旧版本保留，历史批次按原版本可重放） | F16,F17 | `integration:write` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `GET /ingest/dedup-candidates` | `DedupCandidate.list` | 疑似重复实体（同一 SKU/供应商/客户的不同叫法） | INT01,P08 | `integration:read` | — | 可读（L1） | 推断 |
| `POST /ingest/dedup-candidates/{id}/merge` | `DedupCandidate.merge` | 合并重复实体（保留别名与全部来源，引用自动改指） | P08 | `integration:write` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /ingest/batches/{id}/issues/{issueId}/escalate` | `CleansingIssue.escalate` | agent 自动处理未果时转交上传该批数据的人（附 agent 尝试记录、证据与建议） | F02,INT01 | `integration:import` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |

### 5.25 数字孪生与推演（`twin`，15 个）

| 方法 路径 | 实体动作 | 用途 | 页面 | 权限点 | 日志 | AI | 来源 |
|---|---|---|---|---|---|---|---|
| `GET /twin/overview` | `TwinState.list` | 企业孪生总览：店铺、SKU、库存、在途、资金、人员的当前状态与新鲜度 | D01,D03 | `report:read` | — | 可读（L1） | 推断 |
| `GET /twin/state/{type}/{id}` | `TwinState.get` | 单个实体孪生状态（支持 asOf 时点回看；按实体读权限） | F22,I02 | `authenticated` | — | 可读（L1） | 推断 |
| `GET /twin/sync-status` | `TwinState.list` | 各数据源同步频率、最后同步时间、延迟与保真度 | INT02,INT05 | `report:read` | — | 可读（L1） | 推断 |
| `GET /twin/drifts` | `TwinDrift.list` | 孪生偏差：系统状态与外部事实（平台库存、银行流水、物流轨迹）对不上的地方 | F06,I17 | `report:read` | — | 可读（L1） | 推断 |
| `POST /twin/drifts/{id}/resolve` | `TwinDrift.resolve` | 纠偏（agent 优先处理）：非钱账偏差可直接修正；钱和账偏差只生成盘点/调整/冲销草稿走审批 | F06,I17 | `stock_reconciliation:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `GET /twin/snapshots` | `TwinSnapshot.list` | 历史快照（日终、月结、关键事件） | D01,F25 | `report:read` | — | 可读（L1） | 推断 |
| `POST /twin/snapshots` | `TwinSnapshot.create` | 手动打快照（日终与月结快照由系统自动生成） | D01 | `report:create` | 记 | 低风险：自动执行（L3） | 推断 |
| `POST /twin/scenarios` | `TwinScenario.create` | 新建推演（从快照或当前状态派生孪生副本） | F10,I13 | `report:create` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /twin/scenarios/{id}` | `TwinScenario.get` | 推演详情与假设 | F10,I13 | `report:read` | — | 可读（L1） | 推断 |
| `POST /twin/scenarios/{id}/simulate` | `TwinScenario.simulate` | 在副本上执行实体动作（补货、调价、改费率），只写副本 | F10,I13,I20 | `report:create` | 记 | 低风险：自动执行（L3） | 推断 |
| `GET /twin/scenarios/{id}/diff` | `TwinScenario.read_diff` | 推演结果与基线对比（库存天数、现金、毛利） | F10,I13 | `report:read` | — | 可读（L1） | 推断 |
| `POST /twin/scenarios/{id}/promote` | `TwinScenario.promote` | 把推演中选定的动作转成真实草稿，逐条按原动作权限复核并走审批 | I13,I20 | `report:submit` | 记 | 高风险：起草待审，按审批规则生效（L2） | 推断 |
| `POST /twin/drifts/{id}/accept` | `TwinDrift.accept` | 确认偏差属于已知时间差或口径差，不纠偏（写原因；agent 可处理非钱账偏差，钱和账偏差须人确认） | F06,I17 | `stock_reconciliation:approve` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |
| `POST /twin/scenarios/{id}/archive` | `TwinScenario.archive` | 归档推演（副本只读保留） | F10,I13 | `report:write` | 记 | 低风险：自动执行（L3） | 推断 |
| `POST /twin/drifts/{id}/escalate` | `TwinDrift.escalate` | agent 自动处理未果时转交该数据源的上传人/负责人（附尝试记录与证据） | F06,I17 | `stock_reconciliation:create` | 记 | 中风险：自动执行，可撤销（L3） | 推断 |

---

## 6. 与前端已声明接口的差异（契约调整 27 处）

前端注释里共声明了 278 个不重复接口：本设计原样采纳 251 个，调整 27 个。前端函数签名和返回类型不变，只改 service 函数内部请求的地址。

| 前端声明 | 本设计 | 理由 |
|---|---|---|
| `POST /expense/claims/{id}/decide`、`POST /finance/vouchers/{id}/decide`、`POST /procurement/orders/{id}/approve`、`.../reject`；以及无注释的 `approveLandedCostVoucher`、`approvePeriodReopen`、`approveLeave`、`approvePayroll` | `POST /approvals/{id}/decide`（唯一决定入口） | 职责分离、内容哈希、金额门槛、IM 审批、审计只在一处实现。前端适配：先用 `GET /approvals?targetType=&targetId=&scope=todo` 取到待审批单号，再调用 decide |
| `POST /approvals`（两处 `submitAgentSuggestion`） | `POST /agent/suggestions` | 建议由服务端生成 `origin=agent` 草稿和审批项，并强制绑定发起人 |
| `GET /audit`、`GET /audit/events`、`GET /audit?module=...` | `GET /audit/logs?actorType=&category=&module=&refId=` | 一条日志、多个视图（02 第 14.1 节） |
| `GET /security/events` | `GET /audit/security-events` | 与 02、04 文档一致 |
| `GET /notifications`、`POST /notifications/{id}/read` | `GET /notify/messages`、`POST /notify/messages/{id}/read` | 前端有两套收件箱（gap-c / gap-e），合并成一套 |
| `GET/PATCH /admin/notifications` | `GET/PATCH /notify/rules` | 通知规则归通知模块 |
| `GET /admin/integrations` | `GET /integrations/platform-auths` | 归集成模块 |
| `GET /org/departments` | `GET /hr/departments` | 组织归人事模块 |
| `GET /agent/knowledge/documents` | `GET /kb/docs`（可按智能体绑定的空间过滤） | 智能体知识库与企业知识库合并（02 第 12.1 节） |
| `GET /dashboard?store_id=&period=` | `GET /dashboard/summary?storeId=&period=` | 资源化命名 |
| `POST /agent/mode` 与 `PUT /agent/mode` 并存 | 只保留 `PUT /agent/mode`，新增 `GET /agent/mode` | 去重 |
| `PUT` 与 `PATCH /agent/autonomy-policies/{id}` 并存 | 只保留 `PATCH` | 去重 |
| `DELETE /catalog/bundles` | `POST /catalog/bundles/deactivate` | 业务数据只作废不删除（05 第 3 节：删除 L0） |
| `GET/PUT/DELETE /admin/role-overrides`、`/admin/roles/{role}/visibility`、`/crm/role-overrides*`（6 个函数） | 不实现，由 `PUT /admin/roles/{id}/permissions` 取代 | 这是演示用的前端角色可见性覆盖。真实系统由权限矩阵管理 |
| `GET /gap-d/pages/{pageId}`、`GET/POST /{module}/...`（批次 B/D 的通用占位出口） | 拆成各模块的具体接口（第 5 节） | 占位接口不能做权限和审计 |

前端未对上接口的 11 个函数：6 个角色覆盖函数（不实现）、`finance.financeCreatorId`（纯前端工具函数）、`gap-b.fetchGapBPage/submitGapBAction`、`gap-d.fetchGapDRecords/saveGapDOperation`（通用占位出口，已拆分）。

---

## 7. 业务口径（中国会计准则；凡待定一律用演示默认值，真实使用前需核实）

| 口径 | 设计 | 落到哪个接口 |
|---|---|---|
| 准则与主体 | 企业会计准则；**单法人、不做多租户**（maken 已定）；`company_id` 预留但不启用（07 第 B-5.6 节） | 全局 |
| 外部账套 | 顺序：**先金蝶**（Excel 导出，已有目标）→ **再用友** → 其他（如 ERPNext）；所有导出仍只经 ledger 唯一出口 | `/integrations/ledger-targets/*` |
| 审批 | 默认单级，**不设金额上限**，有审批权限即可批；职责分离保留（提交人、被代表人不能审批）；反结账申请人不能自批 | `/approvals/{id}/decide`、`/workflow/rules` |
| 本位币 | CNY；原币与本位币双记 | Money、凭证行 |
| 存货计价 | **移动加权平均**；库存商品 **1405**，在途物资 1402（建议编号，演示默认值，真实使用前需核实；07 第 0.3.1 节注明部分资料写作 1406） | `GET /inventory/stock-ledger`、`/accounting/inventory-reconciliation` |
| 到岸成本 | 头程费用按计费重分摊到批次 × SKU，尾差进最后一行；审批后重估成本层（参考 ERPNext Landed Cost Voucher / Odoo stock.landed.cost） | `/accounting/landed-cost-vouchers*` |
| 暂估 | 货到票未到时贷记暂估应付，票到时冲回，差额进成本调整（ERPNext Stock Received But Not Billed） | `/accounting/grni`、收货接口 |
| 汇兑损益 | 已实现与未实现分开记；期末重估生成凭证草稿；**默认不自动冲回**（演示默认值，真实使用前需核实） | `/accounting/fx-revaluations*` |
| 出口退税/免税 | 只跟踪资料与进度并做齐套校验，不对外申报；退税率按商品配置（演示默认值） | `/tax/export-rebates*` |
| 海外 VAT | **平台代扣代缴的只记录，不计提**；只有「卖家自行负责」的站点才用销项/进项科目（07 第 B-5.7 节） | `/tax/vat-returns*` |
| 凭证规则 | 沿用方案 A（平台应收为中轴）；一行只借或只贷；借贷必须平衡；**未审批不过账**；占位科目编码拒绝过账 | `/finance/vouchers*`，经 ledger |
| 结账 | 结账清单全部通过才能结账；反结账需审批，申请人不能自批（ERPNext Period Closing Voucher） | `/accounting/periods*` |
| 冲销 | 已过账凭证只能生成全额红字冲销 | `/finance/vouchers/{id}/reverse` |
| 期初 | 导入、试算平衡、审批启用后锁定 | `/accounting/opening*` |
| 补货 | 可用量 = 在库 + 在途 − 占用（07 第 C-5.1 节）；安全库存 × 交期 × 渠道；按箱规取整；结果只是计划，转成采购单要人确认（ERPNext Material Request / Odoo 补货规则） | `/inventory/replenishment/*` |
| 薪资 | 规则引擎按配置计算（累计预扣法、社保公积金基数上下限）；未核实的规则版本不能用于正式算薪；AI 不参与计算 | `/hr/payroll-*` |

ERPNext / Odoo 的对照来自前端 `pageCatalog` 中每页的 `erpnextRef` / `odooRef` 字段和 07 文档第 A-2、B-2、C-2 节。本设计借鉴它们的单据两层状态、冲销代替删除、成本层与到岸成本、期间结账凭证。没有复制它们的代码。

---

## 8. 分期建议与前端切换

### 8.1 分期（按「底座 → 主数据 → 业务主流程 → 财务 → 智能体」）

| 期 | 内容 | 接口数 | 累计可接真实数据的页面 | 说明 |
|---|---|---|---|---|
| **P0 底座** | 平台底座（认证、me、文件、任务、店铺、幂等、错误码）、系统与权限（权限表引擎、角色继承、数据范围、字段权限、职责分离）、统一操作日志扩展、审批中心升级、**实体目录与动作执行器、实体版本** | 88 | 41 | 先把旧的 15 个权限点映射到前端目录，避免权限漂移（参考近期出现的 15 个角色权限差异） |
| **P1 主数据 + 快赢** | 商品与主数据；把**已有服务**的结算对账接口（导入、结算、对账、异常、利润、科目、汇率、映射、导出，共 24 个）包成 JSON；**数据进入链路**（落地、清洗、去重、投射、溯源；agent 先处理清洗问题，处理不了转交上传人，P4 智能体上线前直接转交上传人；现有 import_batch/raw_row 升级） | 64 | 61 | 已有服务的财务接口最容易切换，核心计算无需重写 |
| **P2 业务主流程** | 订单、库存（含移动加权库存台账）、补货计划、采购、物流、站内通知、工作台 | 111 | 109 | 打通「补货 → 采购 → 收货 → 头程 → 出库」 |
| **P3 财务** | 其余结算与资金（应收应付、核销、清分）、总账与成本核算、税务、费用报销与预算；**数字孪生与推演**（偏差 agent 先处理，处理不了转交上传人；P4 前直接转交） | 86 | 152 | 依赖 P2 的库存流水；全部按 L2，并且只能经 ledger 写账；推演只写副本 |
| **P4 智能体** | 智能体中心（档案、会话、建议、工具注册表、自主等级、DeerFlow SDK、外部 MCP（可选））、知识库（含所有空间的 AI 整理与体检）、平台集成（Amazon → Shopify → 领星）、外部账套（金蝶，然后用友）、**委托通行证 + DeerFlow SDK 嵌入 + 5 个进程内工具 + 风险分级** | 103 | 198 | 已有 9 个只读工具可以复用；DeerFlow 不单独部署，复用清单见第 10.6 节 |
| **P5 扩展** | 人事与薪资、行政、CRM、广告；**IM 审批（后期）** | 77 | 237 | 前端模块注册表里人事、行政默认关闭 |

每期结束都要：
- 跑 Alembic 迁移往返测试：MySQL 8.4 为主，SQLite 保留演示；
- 补权限测试和审计断言；
- v2：对每个新动作跑「同一动作经网页、agent（主智能体和子智能体，带委托通行证）、导入投射三条路径，结果和拒绝原因一致」的测试；
- 在 21 角色 × AI 开/关 下跑真实接口回归；
- 不删除已有测试。

### 8.2 前端从假数据切到真实接口（契约不变）

1. **保留 `src/api/*.ts` 的函数签名和返回类型**，只替换函数内部实现。`mock-client.ts` 注释里本来就写着「以后把函数体换成请求 /api/v1，返回类型保持不变」。
2. 新增 `src/api/http.ts`，统一处理：
   - `credentials: 'include'`；
   - CSRF 头；
   - POST 自动生成 `Idempotency-Key`；
   - 把错误码映射成现有的 `FlowError`；
   - 401 时跳转登录页。
3. **按模块开关**：
   - `VITE_API_MODE=mock|real` 控制全局；
   - `VITE_API_REAL_MODULES=catalog,fin,...` 控制哪些模块已切到真实接口。
   - 每个 service 文件内部用 `isReal('catalog') ? http.get(...) : mockImpl()`。
   - 这样可以按第 8.1 节的分期逐个模块切换，没切的模块继续用假数据。
4. **类型对齐**：
   - 用 `openapi-typescript` 从后端自动生成的 OpenAPI 产出类型；
   - 增加一个编译期检查文件，断言生成的类型可以赋值给 `src/types` 里的现有类型；
   - 契约一旦漂移，`typecheck` 直接失败。
5. **会话**：真实模式下 `session` store 从 `GET /auth/me` 取数据；`permissions` store 用后端返回的有效权限点。前端的 `assertPermission` 保留，只用来改善体验，权限以后端为准。
6. **审批入口适配**：`approvePurchaseOrder`、`decideGapAClaim` 等函数内部改成「查待审批单号 → `POST /approvals/{id}/decide`」，页面不用改。
7. **双跑验收**：现有点击验证脚本分别对 mock 和 real 各跑一遍，结果一致才把该模块加进 `VITE_API_REAL_MODULES`。

---

## 9. 实体模型与数据进入链路（v2 新增，本次修订的核心）

maken 的要求是：以数据类型为核心，类似本体论或面向对象。凌乱的数据进来后先清洗，再投射成系统预制的实体，然后由系统内部调度执行。本章把这个要求落成三条规则：

1. **先有实体，后有接口。** 系统里每一种业务对象都在实体目录里登记：属性、关系、状态机、允许的动作，每个动作对应一个权限点。
2. **接口只是动作的投影。** 529 个 HTTP 接口全部映射到「实体.动作」。网页、agent 工具、IM 卡片（后期）、定时任务、导入投射、推演副本，调的都是同一个动作执行器，走同一套检查。
3. **外部数据一律先落地再投射。** 原件不可变，清洗、去重、映射都有版本。任何一个实体字段都能追回到原件的哪一行、用的是哪一版规则、是谁在什么时候导入的。

实体目录全文见仓库附件 [`08/ontology-entities.yaml`](08/ontology-entities.yaml)，它由脚本从实体源表和接口清单生成，和 OpenAPI 保持一致。OpenAPI 里每个操作的 `x-crosserp.entity` 和 `x-crosserp.action` 字段注明它投影的是哪个实体动作。

### 9.1 本体层：五个要素

这里的结构参照 Palantir Ontology 公开文档的四个要素：object type（实体类型）、property（属性）、link type（关系）、action type（动作）。动作是「一次性完成的一组修改加上副作用」，并且要校验执行人是否有权限（来源：<https://www.palantir.com/docs/foundry/ontology/core-concepts>、<https://www.palantir.com/docs/foundry/action-types/overview>）。CrossERP 在这四个要素之外再加一个**状态机**，因为 ERP 单据的合法性主要看状态。

| 要素 | CrossERP 的含义 | 例子（采购单 `PurchaseOrder`） |
|---|---|---|
| 实体类型 | 一类业务对象；分 6 类（见下表） | `PurchaseOrder`，模块 proc |
| 属性 | 字段、类型、是否敏感；统一带 `version`（乐观锁）、`provenance`（来源批次/原件行/动作/操作者/被代表人） | `supplierId`、`lines[]`、`total: Money`、`origin: human/agent/system` |
| 关系 | 实体之间的有名关系，用于溯源、权限传递和孪生聚合 | `from → Supplier`、`originatedFrom → ReplenishmentPlan`、`receivedBy → PurchaseReceipt` |
| 状态机 | 状态和合法转移；每个转移都写明由哪个动作或事件触发 | draft → pending（`PurchaseOrder.submit`）→ approved（`Approval.decide`）→ partially_received（`PurchaseReceipt.create`）… |
| 动作 | 查询或命令；每个动作有权限点、AI 自主等级上限、发出的事件、对应的接口 | `PurchaseOrder.submit`：`purchase_order:submit`，agent 风险分级「高」（须人工审核，L2），发出 `purchase_order.submitted`，投影为 `POST /procurement/orders/{id}/submit` |

**规模（脚本统计）**：166 个实体类型、500 个动作，529 个接口全部归属到实体动作，没有游离接口。按类别分：

| 类别 | 数量 | 说明 |
|---|---|---|
| 业务实体 `entity` | 84 | 有状态机，只能通过动作改变 |
| 孪生状态实体 `twin` | 4 | 库存头寸 `InventoryPosition`、头程在途 `Shipment`、资金流水 `CashTransaction`、员工 `Employee`。由外部事实同步加本系统流水推导而来 |
| 只追加记录 `record` | 23 | 库存流水、操作日志、原始记录、实体版本等。不可修改，只能冲回 |
| 配置对象 `config` | 34 | 角色、映射规则、自主等级策略、工具注册等 |
| 元数据/治理 `meta` | 8 | 实体类型、动作类型、事件类型、权限点、连接器等 |
| 只读投影 `view` | 13 | 工作台、利润、总账余额、应收应付等。它们**不是实体**，不能被动作改变，只由实体计算得出 |

另有 12 个实体登记了孪生同步来源：店铺、SKU、Listing、订单、库存头寸、头程在途、结算单、汇率、资金流水、广告、评价、员工。

**主要实体（按业务链）**：

- 主数据：`Store` 店铺、`Sku`、`SkuCost`、`Listing`、`SkuMapping` 平台 SKU 映射、`Bundle`、`Supplier`、`Customer`、`Warehouse`、`Employee`、`Department`、`Account` 会计科目。
- 业务单据：`SalesOrder`、`SalesReturn`、`ReplenishmentPlan`、`PurchaseOrder`、`PurchaseReceipt`、`Shipment`、`InventoryDoc`、`StockCount`、`ExpenseClaim`、`PayrollRun`、`Ticket`。
- 账务：`Settlement` 结算单、`ReconRun`/`ReconIssue` 对账、`Voucher` 凭证、`AccountingPeriod`、`CogsRun` 成本结转、`LandedCostVoucher` 到岸成本、`Clearing` 核销、`VatReturn`、`ExportRebateCase`。
- 流水与事实：`StockMovement`、`CashTransaction`、`TrackingEvent`、`AuditLog`、`EntityVersion`。
- 数据进入：`IngestBatch`、`RawRecord`、`CleansingIssue`、`MappingRule`、`DedupCandidate`。
- 孪生与推演：`TwinState`（视图）、`TwinSnapshot`、`TwinDrift`、`TwinScenario`。
- 治理：`Approval`、`Role`、`PermissionPoint`、`ActionType`、`EventType`、`Delegation` 委托令牌、`AgentSuggestion`、`AgentRun`。
- 知识：`KnowledgePage`、`KbSpace`、`KbCompileRun`、`KbLintFinding`。

### 9.2 接口是实体动作的投影

```text
网页 /api/v1 ─┐
agent 工具（DeerFlow SDK 进程内调用）─┤
IM 卡片回调 ──────┤
定时任务（CrossERP 调度器）─┼─→ ActionDispatcher.execute(principal, "PurchaseOrder.submit", params)
导入投射（IngestBatch.project）─┤
推演副本（TwinScenario.simulate，写副本存储）─┘
```

`ActionDispatcher` 是唯一的动作执行器。路由层只做三件事：认证、解析参数、调用执行器。执行器依次检查以下各项，**人和 agent 用的是同一份代码**：

1. 解析调用人。人：会话或 API Token。agent（含子智能体）：委托通行证，解析出被代表人（第 10 章）。
2. 权限点，拒绝优先（第 4.2 节）。
3. 数据范围与字段权限。
4. 状态机是否允许这个转移，不允许返回 409 `ILLEGAL_TRANSITION`。
5. 职责分离，不能自批。
6. 仅 agent：风险分级与自主等级上限（只读直接放行；改账的动作最高 L2；中风险参数会改银行信息、金额、科目、汇率、成本时按 L2 处理）、委托作用域、发起人与会话核对。v4 取消次数限额。
7. 业务校验：确定性计算，LLM 不算钱（ADR 0002）。
8. 在同一事务里写实体新版本（`EntityVersion`）、操作日志（哈希链）和事件 outbox。
9. 提交后把事件分发给订阅者：调度器、通知、孪生刷新、知识编译。

**对现有 22 个模块和 473 个接口的处理**：

- 473 个接口的路径和契约全部不变（前端零改动）。每个接口在 OpenAPI 里补上 `x-crosserp.entity/action/actionKind`，覆盖表新增「涉及实体」和「实体动作」两列。
- 原先分散的导入入口不再各写一套清洗逻辑，统一成 `IngestBatch` 的动作：`/finance/imports`、`/integrations/imports`、`/ads/imports`、`/hr/attendance/imports`、`/accounting/opening/imports`。列映射 `/finance/column-maps` 和费用映射 `/finance/fee-map` 统一成 `MappingRule`。
- 新增 3 个模块：本体与实体目录 `onto`（8 个接口）、数据进入与溯源 `ingest`（11 个）、数字孪生与推演 `twin`（14 个）。模块总数由 22 变为 25。
- v2 新增接口 55 个，接口总数 473 → 528，路径数 387 → 439（v3 再新增 2 个「转交上传人」接口，见第 9.3、9.5 节，合计 530 个、441 个路径；v4 删 3 个、增 2 个，合计 529 个），详见第 5 节各模块表中「来源=推断」的行：
  - 本体 8 个：实体类型、动作清单、动作预检、事件类型、实体版本、溯源；
  - 数据进入 11 个；
  - 孪生 14 个（含孪生状态查询）；
  - 委托令牌 3 个（v4 删除签发和作废，只留管理员审计用的只读列表）；
  - 知识编译与体检 8 个；
  - **状态机补齐 11 个**。这 11 个是状态机里存在、但现有页面上没有操作入口的转移：异常订单关闭、库存单据红字冲回、询价发出、对账单异议、驳回凭证修改、退税登记已申报、借款付款、客户停用、商机输单、部门停用、资产处置。
- 补齐后，所有状态机转移都能找到触发它的动作或事件，脚本检查缺口为 0。

### 9.3 数据进入链路：原件 → 清洗 → 去重 → 实体 → 版本 → 调度

| 阶段 | 做什么 | 落到哪个实体 / 接口 | 失败时 |
|---|---|---|---|
| 1 落地 | 文件或接口返回的内容原样保存为 `FileObject` + `RawRecord`，记录 SHA-256、来源、接收时间；同一原件重复上传直接返回已有批次（现有导入已按文件哈希去重） | `IngestBatch` uploaded→landed；`GET /ingest/batches/{id}/raw-records` | 原件永不修改、不删除 |
| 2 清洗与校验 | 统一编码、日期、时区、币种、单位；按 `MappingRule` 的**指定版本**解析列；校验必填项、金额精度（万分位）、期间、借贷方向 | `CleansingIssue`、`MappingRule` | 问题行进隔离区，其余行继续；**v3：agent 先自动处理**（补映射、判重复、忽略并写原因），处理不了的转交上传这批数据的人（`POST /ingest/batches/{id}/issues/{issueId}/escalate`） |
| 3 去重与实体解析 | 先按自然键精确去重（订单号+店铺、结算 ID、文件哈希）；再处理「同物不同名」：SKU、供应商、客户的别名。确定性规则优先；**v3：非钱账实体（如 SKU 别名、客户别名）agent 可直接合并**（中风险，可撤销）；涉及供应商银行信息、结算、凭证的合并降为人工确认 | `DedupCandidate`；`POST /ingest/dedup-candidates/{id}/merge` | 合并保留所有别名和全部来源，引用自动改指 |
| 4 投射 | 通过校验的记录转成实体动作，例如 `Settlement.create`、订单状态更新、`StockMovement` 追加。和人工操作走同一个执行器；钱和账相关只生成草稿 | `POST /ingest/batches/{id}/project` | 幂等：同一原件 + 同一规则版本结果相同 |
| 5 版本与溯源 | 每次投射写一条 `EntityVersion`：来源批次、原件行号、规则版本、操作者、被代表人 | `GET /entities/{type}/{id}/versions`、`/lineage` | 可以从凭证一路追回原件行 |
| 6 事件调度 | 实体事件进 outbox，调度器按订阅执行下一步：结算入库触发对账，库存变化触发补货预警和孪生刷新，新资料触发知识编译 | `GET /ontology/event-types` | 订阅者失败可重试，不回滚已提交的实体 |

- **投射以谁的身份执行**：以导入发起人的身份（agent 发起时以被代表人身份），对每个目标动作重新校验权限。导入权限 `integration:import` 不等于能写凭证。
- **v3：清洗问题由谁处理**（maken 决定）：
  1. agent 先处理。它以批次上传人的委托身份执行，可以补映射、判重复、按规则忽略并写原因；每次尝试记在 `CleansingIssue.agentAttempts`。
  2. agent 处理不了（规则冲突、证据不足、连续 2 次失败，或命中「钱和账需人工确认」），就转交上传这批数据的人（`assigneeUserId` 默认等于批次上传人），附上 agent 的尝试记录、证据和建议，在待办和站内通知里出现。上传人已离职或停用时，转给模块管理员。
  3. agent 的处理同样受风险分级约束：结论会改变金额、科目、汇率、成本的，只生成待确认项，由人确认后生效。
- **规则升级与重算**：映射规则升级后不改历史批次。需要重算时，用新批次替代旧批次（`POST /ingest/batches/{id}/supersede`），旧投射通过补偿事件冲回。已过账的部分只能红字冲销，不删除。
- **各类来源走同一条链路**：平台结算报告、订单报告、广告报表、考勤、期初、银行流水、海外仓库存、物流轨迹，只是 `IngestBatch.kind` 不同。平台 API 同步（`SyncJob`）只是自动产生批次。

### 9.4 版本、溯源与事件

- **版本**：实体每次变化都写一条 `EntityVersion`，内容包括谁、何时、经哪个动作或批次、字段级差异。敏感字段只记「已修改」。版本和操作日志在同一事务内写入，操作日志继续使用现有哈希链（ADR 0003）。
- **溯源**：`GET /entities/{type}/{id}/lineage` 返回一张图：文件 → 原始行 → 映射规则版本 → 实体版本 → 实体 → 凭证 → 导出包。调用人看不到的节点只显示「无权查看」，不泄露内容。这与 Digital Twin Consortium 所说的 digital thread 一致：借助稳定的标识，把一个对象在时间和生命周期上的信息串起来（来源：<https://www.digitaltwinconsortium.org/2020/12/the-case-for-the-digital-thread/>）。
- **事件**：命名为 `实体.过去式`，例如 `purchase_order.submitted`。实体目录给每个命令动作标注了它发出的事件。事件和实体修改在同一事务里写入 outbox，提交后再分发，沿用 02 文档第 5 节「同一事务边界」的原则。

### 9.5 数字孪生：企业的实时副本

这里采用 Digital Twin Consortium 的定义：数字孪生是现实实体和流程的虚拟表示，按**指定的频率和保真度**与现实保持同步。它用实时和历史数据表示过去与现在，并用来模拟预测未来。同步有两个方向：从现实到虚拟（观察），从虚拟到现实（干预）。来源：<https://www.digitaltwinconsortium.org/2020/12/digital-twin-consortium-defines-digital-twin/>、术语表 <https://github.com/digitaltwinconsortium/dtc-glossary/blob/main/glossary.md>。Palantir 文档也把 Ontology 称作「组织的数字孪生」（core-concepts 页）。可参考的标准有 ISO/IEC 30173:2023（数字孪生概念与术语，<https://www.iso.org/standard/81442.html>）和 ISO 23247（制造业数字孪生框架，<https://www.iso.org/standard/75066.html>）。这两份标准**正文未读，只引用了官方摘要，细节未核实**。

**孪生范围与同步**（频率和来源都是推断，真实使用前需核实）：

| 孪生对象 | 实体 | 外部事实来源 | 同步频率（演示默认值） | 本系统推导 |
|---|---|---|---|---|
| 店铺 | `Store` | 平台授权状态、结算报告 | 每日 + 事件 | 订单、结算、广告聚合 |
| SKU / Listing | `Sku`、`Listing` | Listing 报告 | 每日 | 成本、毛利、库存天数 |
| 库存 | `InventoryPosition` | FBA 库存报告、海外仓 API | 每日 + 事件 | 由 `StockMovement` 推导的账面数 |
| 在途货 | `Shipment` | 物流商轨迹 | 每 6 小时 | 发运、到仓、在途物资金额 |
| 资金 | `CashTransaction` | 银行流水、平台打款 | 每日 | 应收应付、核销 |
| 员工 | `Employee` | 人事录入、考勤导入 | 每日 | 部门编制、人力成本（敏感，按字段权限） |

**四个机制**：

1. **状态同步（现实 → 孪生）**：外部事实只经数据进入链路投射，孪生不另开写入口。每个孪生状态都带 `asOf`、来源和新鲜度；`GET /twin/sync-status` 显示每个来源的延迟。孪生 → 现实只有一条路：经审批的实体动作，以及写账出口。孪生本身从不直接改外部系统。
2. **对账纠偏**：定时比对「系统推导值」和「外部事实值」，例如账面库存和 FBA 报告、应收和银行到账、在途和轨迹签收。对不上的记为 `TwinDrift`。**v3 处理顺序（maken 决定）**：agent 先处理，可以分类偏差、修正非钱账偏差（例如 Listing 状态、评价数、员工资料同步差异）、把已知时间差标记为接受（`/accept`，写原因）；处理不了的转交该数据源的上传人或负责人（`POST /twin/drifts/{id}/escalate`）。**钱和账偏差**（库存数量与金额、资金、结算、在途金额）只生成盘点、调整或冲销**草稿**走审批（`/resolve`），也不能由 agent 直接接受，不直接改账。
3. **历史快照**：逐次变化记在 `EntityVersion`。另外按日终、月结、关键事件打 `TwinSnapshot`，内容带哈希。任意时点都可以回看（`GET /twin/state/{type}/{id}?asOf=`）。月结快照与会计期间锁定一致。
4. **模拟推演只用副本**：`TwinScenario` 从快照或当前状态派生副本。用户或 agent 在副本上执行实体动作，例如加补货、改头程方式、改售价或费率（`POST /twin/scenarios/{id}/simulate`）。这些动作经过同一套参数、状态机和业务校验，但只写进隔离的推演存储：**不写真实实体，不写账，不发外部消息**。在推演里写账类动作一律返回 `SCENARIO_READ_ONLY`。结果用对比视图展示：库存天数、现金占用、毛利。选中的动作可以「转为真实草稿」（`/promote`），每条按原动作的权限和自主等级重新复核，再进审批。这个做法参照 Palantir Ontology Scenarios 的「沙箱化的数据分叉，不影响生产数据」（来源：<https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/ontology-scenarios/ontology-scenario-basics>）。CrossERP 的区别是：推演结果**不能直接合并回真实数据**，只能转成草稿走审批。
5. 补货计划（`ReplenishmentPlan`）和利润测算都改成读孪生快照（`basedOnSnapshot`），这样同一份输入可以重放，结果也可以解释。

### 9.6 企业知识库：知识持续积累，并且按权限访问

知识库从「文档仓库加检索」升级为「挂在实体上的、持续编译的知识」：

- **三层**：原件（不可变）→ 知识页 `KnowledgePage`（由 AI 维护草稿；空间配了审核人就由审核人发布，没配就由 AI 直接发布并留痕，v4）→ 规则（空间定位、页面类型、引用格式，写在空间配置里）。
- **知识页和实体互相挂接**：知识页的 `links` 指向实体，例如某个 SKU、供应商、平台费用规则；`sources[]` 指向原件、实体或问答。在实体详情页可以直接看到这个实体的知识页（`GET /kb/entity-pages/{type}/{id}`）。
- **增量编译**：新资料到达，或实体发生事件（例如工单已解决、映射规则升级），会触发 `KbCompileRun`。它先按内容哈希跳过没变的来源，再分两步：先分析，再生成知识页草稿和审核项。发布仍走 `kb/reviews` 人工审核。
- **体检**：`KbLintFinding` 检查孤立页、断链、多页互相矛盾、内容过期，以及**与实体数据不一致**（例如知识页写的费率和当前 `MappingRule` 不同）。最后这一项是 CrossERP 特有的检查。
- **权限**：知识页同时受两层权限过滤：空间 ACL，以及来源实体的读权限。调用人看不到的来源，在引用里只显示「无权查看」。agent 检索时用被代表人的权限。
- **v3：所有空间都由 AI 整理**（maken 决定，包括薪资、合同等敏感空间），访问仍按权限：
  1. 整理任务 `KbCompileRun` 以发起者身份运行；系统定时触发时以该空间管理员身份运行。只读取这个身份有权看的来源，看不到的来源不进入模型上下文。
  2. 产出的知识页写回来源所在的空间，继承该空间的 ACL；一个整理任务只写一个空间，不把 A 空间的内容写进 B 空间。
  3. 跨空间引用只保存链接，不复制内容；读者没有目标空间权限时只看到「无权查看」。
  4. 敏感空间的整理结果不进入公共检索索引，按空间分别建索引；模型调用日志只记摘要和来源 ID，不保存敏感正文（沿用 02 第 12.4 节）。
  5. 整理结果的发布与审批规则对齐（v4）：空间配置了审核人就走审核人；没配置时 agent 直接发布（中风险，可撤销），并留痕「无审核人，直接发布」。

### 9.7 借鉴了什么：llm_wiki、Palantir Ontology、数字孪生

**nashsu/llm_wiki 核实结果**（仓库 <https://github.com/nashsu/llm_wiki>，读的是 commit `e08cfce`；下面的路径相对仓库根目录）：

| 问题 | 它怎么做（已核实） | 来源 |
|---|---|---|
| 是什么 | 跨平台桌面应用（Tauri + React，Rust 后端），基于 Karpathy 的「LLM Wiki」方法论：LLM 增量构建并维护一个持久化的 Markdown Wiki，取代「每次查询都从头 RAG」 | `README_CN.md`；方法论原文 `llm-wiki.md`、<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f> |
| 摄入与清洗 | 原件放 `raw/sources/`，**不可变**。支持 PDF/Office/网页等多格式（可选 MinerU）。**两步思维链摄入**：第一步分析实体、概念、与现有内容的关联和矛盾，第二步生成 Wiki 文件。持久化串行摄入队列，崩溃可恢复、失败最多重试 3 次 | `README_CN.md`「两步思维链摄入」；`src/lib/ingest.ts`、`src/lib/ingest-queue.ts` |
| 清洗 LLM 输出 | 对 LLM 生成的文件做清理：剥离多余包装、修正错误的 `[[wikilink]]` 格式、校验写入路径安全 | `src/lib/ingest-sanitize.ts`（`sanitizeIngestedFileContent`、`normalizeMalformedWikilinks`）；`src/lib/ingest.ts`（`isSafeIngestPath`） |
| 增量更新 | 按原件内容 SHA-256 缓存，没变就跳过；准备阶段可以并发，**提交按任务开始顺序串行** | `src/lib/ingest-cache.ts`；`src/lib/ingest-commit-coordinator.ts` |
| 页面与实体链接 | 每页带 YAML frontmatter（type、title、sources[]），用 `[[wikilink]]` 交叉引用。补链接时，**LLM 只返回「词 → 目标」替换清单，由代码做字符串替换**，防止 LLM 改写正文。多来源的页面在合并时对 `sources/tags/related` 取并集，不覆盖 | `src/lib/enrich-wikilinks.ts` 文件头说明；`src/lib/sources-merge.ts` |
| 去重 | 三步：抽取实体摘要 → LLM 识别疑似同一实体 → 人确认后合并，并改写全库引用 | `src/lib/dedup.ts` 文件头说明 |
| 引用溯源 | frontmatter 的 `sources[]` 指回原件；问答时按编号引用 [1][2]，引用随消息保存 | `README_CN.md`「来源可追溯」「引用持久化」 |
| 一致性检查 | Lint 分两层：结构检查（孤立页、断链、无出链），以及 LLM 语义检查（矛盾 contradiction、过期 stale 等） | `src/lib/lint.ts`（`LintResult.type`；语义提示词含 contradiction/stale）、`src/lib/lint-structural-core.ts` |
| 删除 | 删除原件时级联清理：只从共享页的 `sources[]` 里去掉该来源，不删整页；同时清理失效链接 | `README_CN.md`「文件删除级联清理」 |
| 人机协作 | 摄入时 LLM 把需要人判断的项放进异步审核队列，不阻塞摄入 | `README_CN.md`「审核系统」；`src/stores/review-store.ts` |
| 对外接口 | 本机 `127.0.0.1:19828` HTTP API + MCP Server，默认只读 | `README_CN.md`；`mcp-server/README.md` |
| 许可证 | **GPL-3.0** | `LICENSE`、`README_CN.md`「许可证」 |

**可以借鉴到 CrossERP 的**（只借鉴思路，不复制代码）：

1. 原件不可变，知识或实体与原件分层 → 对应 `RawRecord` 和 `KnowledgePage`，以及「原件 → 实体」的分层。
2. 内容哈希增量跳过 → 用于导入批次和知识编译。
3. 准备阶段并发、提交串行 → 投射与知识编译的提交都按顺序串行，避免并发覆盖。
4. 先分析、后生成 → 知识编译分两步；导入中的 AI 映射建议也分两步：先给分析和候选，再生成映射规则草稿。
5. **LLM 只出清单，由代码执行修改** → 这正是 CrossERP 的原则：agent 只提出动作和参数，由动作执行器做确定性修改（ADR 0002）。
6. 来源取并集，不覆盖；删除时只去掉对应来源 → 用于 `KnowledgePage.sources[]` 和 `DedupCandidate` 合并。
7. 结构检查 + 语义检查 → `KbLintFinding`，另外加上「与实体数据不一致」一项。
8. 可疑项进异步审核 → `CleansingIssue`、`DedupCandidate` 和知识审核项都不阻塞主流程。

**不适用的**：

1. **单用户本地桌面应用，没有权限模型**。它的 HTTP API 可以配置成免令牌访问（`mcp-server/README.md`），没有按用户、按空间的 ACL。CrossERP 必须多用户、按权限过滤，并记操作日志。
2. Wiki 页面以 Markdown 文件为准、由 LLM 直接写入。CrossERP 的业务事实以数据库实体为准，知识页只是解释层，**不能作为记账依据**。LLM 写的内容按空间规则发布：有审核人就先审，没有就直接发布并留痕；无论哪种都不能作为记账依据。
3. LLM 实体抽取和 LLM 去重只能用于知识层。业务主数据（SKU、供应商、金额）的去重和映射必须以确定性规则为主，AI 只提候选。
4. GPL-3.0：如果复制它的代码进 CrossERP 并对外分发，就会触发 GPL 义务。只借鉴设计思路是可以的。
5. 图谱算法（Louvain 社区发现、惊奇连接）属于锦上添花，不进首期。

**Palantir Ontology 借鉴了**：实体/属性/关系/动作四要素；动作是带校验和副作用的一次性提交；所有应用共用同一套动作逻辑；角色控制实体、关系和动作的访问；推演用数据分叉，不影响生产数据。**没有借鉴**：Foundry 的数据集/管道平台和它的写回机制。CrossERP 是模块化单体，实体直接落在业务表里。

**数字孪生借鉴了**：按「指定频率与保真度」同步；双向同步，但虚拟到现实必须经过审批动作；用历史数据和快照回看过去；用副本模拟未来；用 digital thread（稳定标识）串起整个生命周期。ISO 标准只引用了官方摘要。

---

## 10. agent 权限继承与 DeerFlow 集成（SDK 嵌入；v4：独立 worker、无感通行证、OpenAI 兼容模型、禁止执行代码）

> 核实范围：`bytedance/deer-flow` 主干 commit `2a97ec3`（2.3.0-dev；最新正式标签 `v2.2.0`；MIT），2026-11-11 只读克隆，逐一阅读文档和源码。网页链接以 <https://github.com/bytedance/deer-flow/blob/2a97ec3e589821e8435d57ef3f160ef6824b2a45/> 为前缀，下文只写相对路径和行号。**没有实际安装运行**。依赖能否一起安装做了试解析（`uv pip compile`），没有实际安装。

### 10.0 maken 第 12 条：DeerFlow 一定要部署吗？——结论：不用，可以只当 SDK 用

**结论**：DeerFlow 可以作为 Python 库嵌入 CrossERP 的 Python 3.12 进程，不需要单独部署 DeerFlow 的 Gateway、LangGraph Server、前端、nginx，也不强制 Docker、Postgres 或 Redis。v3 改用这种方式：在 CrossERP 自己的 agent worker 进程里用 `DeerFlowClient` 跑智能体。限制有三条：
1. 没发布到 PyPI，要按 git 标签安装；
2. 依赖很重（试解析共 350 个包）；
3. Gateway 专属的能力会丢失，CrossERP 要么自己有替代（认证、IM、定时任务、取消），要么用不上。

| 问题 | 结论 | 依据 |
|---|---|---|
| 能否不起 Gateway / LangGraph Server，直接当库用 | **能** | `backend/packages/harness/deerflow/client.py` L1-4、L177-181：「without requiring LangGraph Server or Gateway API processes」；`docs/guide/api-and-client.md` L57：「can be used as an embedded Python library without running the full HTTP services」；官方 TUI 就是这样跑的，`docs/guide/tui.md` L3：「no Gateway, frontend, nginx, or Docker required」 |
| 安装方式 | **没有发布到 PyPI**：2026-11-11 查询 `pypi.org/pypi/deerflow-harness`、`deer-flow`、`deerflow-extension-api` 都返回 404。包名是 `deerflow-harness`（import 名 `deerflow`），和 `deerflow-extension-api` 一起放在仓库的 `backend/packages/` 下。只能用 git 依赖安装，并锁定 commit 或标签，例如 `deerflow-harness @ git+https://github.com/bytedance/deer-flow@v2.2.0#subdirectory=backend/packages/harness`（具体写法未实测）。发布流程只打 GitHub 标签，没有 PyPI 步骤 | `backend/packages/harness/pyproject.toml` L1-5；`docs/RELEASE_SOP.md` §7 Publish；`AGENTS.md` L42 |
| Python 版本 | `requires-python = ">=3.12"`，`backend/.python-version` 为 3.12。**CrossERP 用的 3.12 满足** | `backend/packages/harness/pyproject.toml` L5；`backend/.python-version` |
| 依赖 | 核心依赖 50 多个直接依赖，包括 langchain≥1.3、langgraph 1.2.x、langgraph-api、langgraph-cli、kubernetes、e2b、markitdown[all]、duckdb、sqlalchemy≥2.0、alembic≥1.13、pydantic≥2.12.5。**和 CrossERP 现有依赖放在一起试解析成功**（Python 3.12，共 350 个包；没有冲突；CrossERP 依赖取自只读快照 `pyproject.toml`）。缺点是体积大，会把 onnxruntime、pandas、kubernetes 等带进 CrossERP 环境 | `backend/packages/harness/pyproject.toml` L6-66；box 试解析 `/tmp/dfres/req.txt` |
| 配置 | 嵌入时仍然要准备 `config.yaml`、`extensions_config.json` 和 skills 目录（官方 RFC 也承认「6 处隐式 I/O」）；可以用 `DeerFlowClient(config_path=...)` 指定一份 CrossERP 专用配置 | `backend/docs/rfc-create-deerflow-agent.md` L18；`docs/guide/api-and-client.md` L64-67 |

**嵌入方式下保留什么、丢掉什么**：

| 能力 | 嵌入模式 | 依据 / 说明 |
|---|---|---|
| 主智能体、规划、上下文压缩 | 保留 | `client.py` 直接调用 `create_agent` + `build_middlewares`（L31-36） |
| 流式输出 | 保留（同步生成器，逐 token 增量，事件类型与 Gateway 一致） | `client.py` L859-1001；CrossERP 在线程池里消费，再转成 SSE 给前端 |
| 子智能体 | 保留（`subagent_enabled=True` 开启，默认关；并发由 `subagent_runtime.max_running` 控制，默认 3） | `client.py` L218、L236、L251-257；`config.example.yaml` L2031-2032 |
| 技能 `SKILL.md` | 保留（`available_skills` 可以限定可用技能） | `client.py` L221、L239 |
| 记忆 | 保留，按 `user_id` 隔离 | `client.py` L1050-1055；`backend/docs/AUTH_DESIGN.md` Memory 节 |
| 自定义工具 | 保留：`config.yaml` 的 `tools:` 用 `use: 模块:变量` 挂进程内 Python 工具；工具通过 `runtime` 参数读取运行上下文 | `config.example.yaml` L849-870；示例 `deerflow/community/ragflow/tools.py` L624 |
| MCP | 保留：stdio/HTTP；静态凭证或按用户的 `user_auth` 可用；**按请求传的 `context.secrets` 不能用**（见下一行）；OAuth token 只存在进程内存 | `backend/docs/MCP_SERVER.md` L232-237、L520-524 |
| **按请求传 secrets** | **不支持**：嵌入的 `stream()` 只把 `user_id、user_role、oauth_provider、oauth_id、channel_user_id、is_internal、authz_attributes` 放进运行上下文，不放 `secrets`。所以 `headers_from_context` 在嵌入模式下拿不到凭证，按 `on_missing: deny` 会拒绝调用 | `client.py` L93-103、L1040-1047；`deerflow/mcp/context_headers.py` L76-91、L185-195 |
| 代表用户的身份 | 保留：调用方是可信方，可以直接传 `user_id`、`authz_attributes`；同一个 client 可以安全服务多个用户 | `client.py` L985-988（docstring「Trusted embedded callers may also provide user_id…」）、L337-341 |
| 授权 Provider | 保留：嵌入路径同样构造 Principal | `client.py` L40 引入 `build_principal_from_context` |
| 自定义中间件 | 保留：构造参数 `middlewares` | `client.py` L222、L240 |
| checkpoint 持久化 | 保留，**不需要 Postgres 或 Redis**：不传 checkpointer 时按 `database.backend` 取（默认 sqlite，文件在 `.deer-flow/data`）；也可以直接传任意 LangGraph checkpointer 实例。不配 checkpointer 时每轮都是无状态的 | `client.py` L183-186、L231-233、L1012-1016；`config.example.yaml` L2679-2773；`deerflow/runtime/checkpointer/provider.py` L6（只支持 memory/sqlite/postgres） |
| 取消运行 | **没有取消接口**。官方 TUI 的做法是停止消费、关闭生成器；正在执行的那次工具调用会跑完 | `client.py` 方法清单里没有 cancel；`deerflow/tui/app.py` L699-712 |
| 沙箱 | 保留；**不是必须 Docker**：默认 `LocalSandboxProvider`，并且默认关闭宿主机 bash（`allow_host_bash: false`）；只有需要执行 bash 或代码时，才要换 AIO（Docker）、E2B 等隔离沙箱。**v4：AI 不执行代码，保持 Local 空壳、不装 Docker（第 10.9 节）** | `config.example.yaml` L1751-1756；`backend/docs/CONFIGURATION.md` L1679、L2029-2032；`docs/guide/sandbox.md` L6-8 |
| 前端 UI | **可以不要** | `docs/guide/tui.md` L3；CrossERP 有自己的聊天界面 |
| Gateway 认证（本地账号/OIDC/PAT/Internal Auth） | 丢失，也不需要：身份由 CrossERP 决定 | — |
| IM 渠道、DeerFlow 定时任务、run events 存储与 `/messages/page`、断线重放（StreamBridge）、Redis checkpoint 缓存 | 丢失。CrossERP 已决定自己调度定时任务（第 1 条），审批先在平台内，IM 放到后期，对话记录存 CrossERP 自己的表 | `client.py` L950-972（嵌入路径不使用 StreamBridge）；`docs/guide/deployment.md` L80-83；`backend/docs/TUI.md` L160-170 |

**两种方式对比**：

| | **A. SDK 嵌入（v3 采用）** | B. 独立部署 DeerFlow Gateway（v2 方案） |
|---|---|---|
| 开发量 | 少：CrossERP 内写进程内工具（直接调用 ActionDispatcher）、一个守卫中间件、对话转 SSE；**不需要** MCP 服务、Internal Auth 对接、网关客户端、取消回调 | 多：CrossERP MCP 服务 + 委托令牌网络传递 + Internal Auth + 网关客户端 + 取消联动 + 用量回写；子智能体凭证还要自写拦截器 |
| 运维 | 不增加服务：随 CrossERP 的 agent worker 一起发布；DeerFlow 状态只是一个 sqlite 文件（或 MySQL checkpointer，见第 11 章）；升级 = 改依赖锁定后重新发布 | 多一套服务：Gateway（+ 可选 nginx/前端）、它自己的数据库、密钥、监控和升级 |
| 隔离 | 智能体代码与 CrossERP 在同一台机器、同一套依赖里运行；要保持宿主机 bash 关闭、不加载来路不明的 stdio MCP 和技能。**建议跑在独立的 agent worker 进程里**，不要放进对外的 API 进程，这样崩溃或内存问题不影响网页 | 进程和机器可以分开，爆炸半径小；但 Gateway 管理员等同于能在主机执行代码，网络边界和内部令牌需要管理 |
| 身份传递 | 进程内传递，没有网络令牌，不会泄露；子智能体自动继承（下文 10.3） | 靠网络令牌加 `headers_from_context`；**子智能体拿不到 secrets，会被拒绝**（代码已确认），需要自写补丁 |
| 依赖风险 | 350 个包进入 CrossERP 环境，DeerFlow 升级可能牵动 CrossERP 的依赖 | 依赖互不影响 |
| 何时改用 B | 需要多台机器横向扩展智能体、要用 DeerFlow 自带的 IM 或 Web UI、或者依赖冲突解决不了 | — |

### 10.1 嵌入后的架构（v4：agent 独立 worker 进程、独立 Python 环境）

```text
浏览器 ──会话──→ CrossERP API 进程（FastAPI，CrossERP 自己的 venv）
                   │ POST /agent/threads/{id}/messages
                   │ ① 核对发起人  ② 系统自动签发或续用委托通行证 D（用户无感）
                   ▼ 写入 MySQL 任务表（现有 job 机制，SKIP LOCKED 领取）
               CrossERP agent worker 进程（独立进程、独立 venv：CrossERP 领域包 + deerflow-harness）
                   DeerFlowClient(config_path="config/deerflow.yaml",
                                  checkpointer=…, subagent_enabled=True,
                                  middlewares=[CrossErpGuardMiddleware])
                   client.stream(text, thread_id=…,
                                 user_id=<CrossERP 用户 ID>, user_role="user",
                                 authz_attributes={"crosserp_delegation_id": D.id})
                     ├─ 主智能体 ──调用──→ crosserp_* 进程内工具 ─→ ActionDispatcher ─→ MySQL
                     └─ 子智能体（task）──同一上下文──→ crosserp_* 工具 ─→ ActionDispatcher
                   事件（token / tool_call / done）写入 run 事件表 → API 进程转成 SSE 推给浏览器
```

- **为什么单独一个进程和环境**（maken 第 1 条）：DeerFlow 带来约 350 个依赖（第 10.0 节）。放在独立 venv 里，API 进程的依赖不受影响；agent 崩溃、内存上涨或升级 DeerFlow，都不影响网页和其他接口。agent worker 用 CrossERP 的领域包（实体目录、`ActionDispatcher`、仓储层）直接访问 MySQL，所以权限检查与网页是同一份代码。
- **两个进程之间只通过数据库通信**：任务表（谁、哪个线程、哪条消息、哪个通行证）、run 事件表（流式输出）、outbox（通知）。不开内部 HTTP 端口。
- worker 的并发：每个对话一个任务，worker 内用线程池消费 `client.stream()`（同步生成器）；同时运行数默认 4（演示默认值）。
- **工具不按 500 个动作一一生成**。只注册 5 个通用工具，用 `use:` 挂载：
  - `crosserp_describe`：列出当前可执行的实体和动作，及其参数结构；
  - `crosserp_query`：查询实体；
  - `crosserp_dry_run`：预检；
  - `crosserp_execute`：执行动作；
  - `crosserp_lineage`：溯源。

  可执行范围在服务端按委托计算。这样工具清单很短，模型上下文不随动作数量增长；配套技能 `SKILL.md` 写业务流程（月结检查、补货、对账、清洗问题处理）。
- 原 v2 的 CrossERP MCP 服务改为**可选**（P5 或之后），只在需要给外部智能体用时再做。

### 10.2 子智能体带着凭证调用工具：核实结果与保证设计

**核实结果（代码阅读，未运行）**：
- **网络 secrets 不会传给子智能体**。子智能体执行器构造子上下文时，只复制以下内容，**没有 `secrets`**：
  - `thread_id`、`user_id`、`user_role`、`oauth_provider`、`oauth_id`、`run_id`；
  - `channel_user_id`、`is_internal`、`authz_attributes`；
  - `is_subagent=True`、`agent_id` 等。

  来源：`deerflow/subagents/executor.py` L1901-1937；`deerflow/tools/builtins/task_tool.py` L988-999。因此 v2 方案「子智能体经 MCP `headers_from_context` 带令牌」**不成立**：子智能体的调用会因为缺少凭证被拒绝。不会越权，但子智能体也就做不了事。
- **`user_id`、`run_id`、`authz_attributes` 会原样传给子智能体**。代码注释写明这些值和 `user_role`、oauth 一样来自服务端（task_tool.py L995-997），模型改不了。

**CrossERP 的保证设计**：
1. **委托只用 ID 携带，不用秘密串**。CrossERP 调用 `stream()` 时放入 `authz_attributes.crosserp_delegation_id`，同时放入 `user_id`。子智能体自动继承这两个值。
2. **工具在进程内回查委托**。`crosserp_*` 工具从 `runtime.context` 读取 `user_id`、`run_id`、`thread_id`、`authz_attributes`、`is_subagent`、`agent_id`，然后在数据库里校验：
   - 委托存在、未过期、未作废；
   - `D.user_id == user_id`；
   - `D.thread_id == thread_id`；
   - 会话或任务绑定仍然有效；
   - 用户未停用；
   - 权限版本未变。

   **任何一项不符就拒绝**。工具参数里的身份字段一律忽略。
3. **为什么只传 ID 也安全**：这些工具只在 CrossERP 的 worker 进程内运行，外部无法调用；ID 只有和服务端记录的「用户 + 线程 + 有效期」同时吻合才有效。拿到一个 ID 并不能在别的线程或身份下使用。
4. **子智能体与主智能体同权**：同一个委托、同一套风险分级（见 10.4），不另开权限。日志里记 `is_subagent` 和子智能体名（`agent_id`），能区分是谁做的。
5. **子智能体不能做 L0（高危）动作**。L2 高风险动作照样只生成待审项。子智能体不能等待人工确认（DeerFlow 对子智能体的确认请求一律拒绝，`backend/docs/RUN_INTERACTION_POLICY.md` L29），所以高风险动作的「人工审核」由 CrossERP 审批中心异步完成，不在对话里阻塞。
6. **回归测试**：主智能体和子智能体各调用一次同一个动作，结果、拒绝原因和日志都必须一致；系统自动作废通行证（例如登出）后，子智能体的下一次调用必须被拒绝。

如果将来改回独立部署（方式 B），用 DeerFlow 支持的自定义 MCP 拦截器 `mcpInterceptors`（`backend/docs/MCP_SERVER.md`），从 `authz_attributes` 读取委托 ID，再由 DeerFlow 主机用自己的服务密钥签名后发给 CrossERP。这只是备选，未实现、未验证。

### 10.3 身份链路（嵌入模式）

1. 浏览器发消息。CrossERP 核对「请求里的 initiator == 会话用户」，不一致返回 409 `AI_INITIATOR_MISMATCH`（只在前端状态错乱时出现，正常使用碰不到）。
2. **系统自动签发或续用**委托通行证 `Delegation`，用户看不到这一步：
   - 绑定用户、会话、线程；
   - `scopes` = 被代表人当前可执行动作 ∩ 智能体收窄 ∩ 本次请求范围；
   - `maxAutonomy` 不超过风险分级上限；
   - 单张最长 24 小时，会话活跃时后台静默续期（第 10.5 节）。
3. agent worker 调用 `client.stream(…, user_id, authz_attributes={crosserp_delegation_id})`。DeerFlow 的记忆、文件和 checkpoint 按这个 `user_id` 隔离。
4. 每次工具调用（主智能体或子智能体）都在 CrossERP 进程内回查委托，再交给 `ActionDispatcher`。执行器的检查和网页完全相同：权限、数据范围、字段权限、状态机、职责分离、风险分级与钱账上限、业务校验。最后在同一事务里写实体版本、操作日志和事件。日志字段：`actor_type=agent`、`agent_id`、`on_behalf_of`、`delegation_id`、`run_id`、`tool_call_id`、`is_subagent`、模型、提示词版本。
5. 流结束时再核对一次发起人；不一致就丢弃结果，不推给前端。
6. 定时任务由 CrossERP 调度（v3 已定）。每次运行时，系统以委托人**当时**的权限自动签发任务通行证（不绑定浏览器会话）。委托人停用或失去权限时，任务自动暂停，并在管理员的任务页显示原因。

### 10.4 风险分级：只看动作改不改数据（v4，maken 第 2、7 条）

所有动作分成 5 级，主智能体和子智能体用同一套规则。级别只看动作会不会改动数据；钱和账的限制只管「改账」：

| 风险 | agent 能做什么 | 自主等级 | 典型动作 | v4 接口数（v3） |
|---|---|---|---|---|
| 无（只读） | 直接查询、解释、提醒 | L1 | 所有列表、详情、报表、溯源；**对账结果、利润、凭证、余额、薪资批次、审计记录等钱和账的查询**；权限和日志的查看 | **258**（224） |
| **低** | 直接执行，不设次数上限 | L3 | 打标签、标已读、**对账计算与匹配**、补货计划、试算、评分、报表运行、建内部工单、推演副本试算、知识体检、生成审计包、测试连通 | **37**（34） |
| **中** | 直接执行；改数据但不改账；24 小时内可撤销；**不设次数限额**；事后只进每日站内摘要 | L3 | 非钱账主数据（SKU、Listing、类目、品牌、仓库、物流商、运费模板）、业务草稿（采购单、询价、合同、运单、退货登记、库存单据草稿）、CRM、知识页草稿与整理、导入落地与投射、清洗问题处理与去重合并、孪生偏差处理与转交、**对账差异处理（已解释/忽略）** | **74**（73） |
| **高** | 可以发起，结果是草稿或待审项，按第 4.6 节审批规则生效；**没有可用审批人时退回发起人本人确认** | L2 | **改账**（生成凭证、调账、结转、汇兑、分摊、核销、付款、报销、借款、折旧）、库存过账/收货/发货/调拨/盘点、对外发送（询价发出、回复买家）、供应商新建与银行信息、成本/汇率/费用映射/广告分摊、各类「提交审批」、推演转草稿 | **56**（57） |
| **危** | **agent 禁用** | L0 | 权限与治理的**写操作**、审批决定、发起人确认、自主等级与风险分级设置、工具注册、密钥与模型设置、日志保留、薪资计算与发布、期末结账、导出写账 | **104**（142） |

调整明细见第 4.4 节（36 个接口改级，删除 3 个，新增 2 个）。

保留的规则：
- **改账的动作最高 L2**。即使在策略里配成更高，执行时也会自动降级并写安全日志。
- **职责分离**：提交人、被代表人、起草草稿的 agent 所代表的人，都不能审批同一张单；反结账按第 4.6 节规则处理。
- **agent 不能执行权限和治理类写操作**（危级），但可以读（帮用户解释「为什么我看不到某个菜单」）。
- **agent 不能自己扩权**：通行证由系统签发，agent 无法签发或续期；作用域只会收窄；风险分级策略只有真人能改，并且只能收紧；DeerFlow 的角色声明一律忽略；发起人确认接口只有真人能调用。

级别的判定在服务端完成，取自实体目录。v3 的「按目标实体动态降级」只保留一种情况：中风险动作的参数会改动银行信息、金额、科目、汇率、成本字段时，按「改账」处理为 L2（例如合并两个重复的「供应商」会改银行信息）。管理员可以按模块、动作、角色把某个动作再收紧一级（`/agent/autonomy-policies`），但不能放宽。

### 10.5 通行证：系统全自动，用户无感（v4，maken 第 3 条）

**原则**：通行证是系统内部的安全机制，不是给用户管理的东西。用户只管和 AI 说话；签发、续期、作废都由系统自动完成，用户既看不到也不用操作。

| 环节 | 怎么做 | 用户感知 |
|---|---|---|
| 签发 | 用户在一个对话里发第一条消息时，系统按会话自动签发；定时任务每次运行时自动签发 | 无 |
| 续期 | 会话还有效时，后台**静默续期**；单张通行证到 24 小时上限前，系统自动签发新的一张并无缝替换，正在进行的对话不中断 | 无 |
| 空闲 | **不再挂起**。v3 的「连续 2 小时无工具调用就挂起」删除。空闲期间通行证照常有效，直到会话本身结束 | 无 |
| 权限变化 | 旧通行证**立即作废**，正在进行的运行停止；用户下次发消息时，系统按新权限**静默重新签发**，不报错、不要求重新登录 | 对话里出现一句「权限已更新，已按新权限继续」 |
| 自动立即作废 | 登出、切换账号、会话过期、改密码、用户停用、管理员关闭 AI 或进入降级模式 | 无（这些本来就是用户或管理员自己的操作） |
| 人工作废 | **取消**。没有「我的通行证」页面，也没有作废按钮 | — |

停止的方式不变：守卫中间件在每次模型调用和工具调用前检查通行证，失效就结束本轮；worker 同时停止消费并关闭生成器。正在执行的那一次工具调用会跑完，它在执行器里会再被校验一次。

保留的后台风控（都不打扰用户）：
1. **每次调用都按当前权限重算**。通行证只证明「谁授权、授权到什么范围」，不缓存权限。
2. **交互式通行证随会话失效**。登录会话规则沿用现有配置（12 小时、空闲 2 小时，`config.py`）；用户在用的时候会话会自动延续。定时任务的通行证绑定任务本身，每次运行重新签发。
3. **作用域自动收窄**：每次请求只带这次需要的实体和动作范围；定时任务只带任务配置的动作。用户不用选。
4. **异常只告诉管理员**：短时间内高风险草稿激增、非工作时间批量操作、连续被拒等，写安全日志并通知管理员；不挂起用户、不给用户发通知。管理员需要时可以用 AI 总开关一键关闭。
5. **不出进程**：SDK 模式下没有网络令牌，委托 ID 在网络上不传输，也不写进模型提示词或 trace（只写 CrossERP 自己的日志）。
6. **可审计**：签发、续期、使用、作废（含原因 `revokeReason`）都写安全日志；管理员可在只读列表 `GET /agent/delegations` 里按通行证复核 agent 的操作。普通用户看不到这个列表。

接口变化：删除 `POST /agent/delegations`（签发）和 `POST /agent/delegations/{id}/revoke`（作废）；`GET /agent/delegations` 改为管理员审计用（权限点 `audit_log:read`），页面从「我的数据范围」（ME01）移除。错误码 `DELEGATION_INVALID`、`DELEGATION_SCOPE_EXCEEDED`、`PERMISSIONS_CHANGED` 只在 agent 工具内部使用，不展示给用户。

### 10.6 复用 DeerFlow 什么，自己补什么（SDK 模式）

**复用**：
- 运行时与主智能体、上下文压缩、子智能体并发控制（只用 `general-purpose` 子智能体）；
- 技能体系（只加载仓库内受控目录的技能，技能只是说明文字，不执行脚本）；
- 按用户的记忆：只记偏好，**不存业务事实**；
- checkpoint（sqlite 文件，第 11.2 节）；
- 授权 Provider 与护栏：作为第二道防线，可选；
- 模型接入：`langchain_openai:ChatOpenAI` 的 OpenAI 兼容配置，以及 managed models「密钥不出服务器、不回显」的做法（第 10.8 节）；
- Langfuse/LangSmith 追踪（可选；不记录委托 ID 和密钥）；
- 上传文件转 Markdown。

**CrossERP 自己做**：
1. 5 个进程内工具，直接调用 `ActionDispatcher`；
2. `CrossErpGuardMiddleware`：调用前检查通行证、只放行白名单工具和子智能体、停止运行（**不再做次数限额和熔断**）；
3. 委托通行证服务（自动签发、静默续期、自动作废）；
4. agent worker（独立进程和 venv；任务队列消费、事件落库、转 SSE）；
5. 模型设置（加密存储、运行时注入，第 10.8 节）；
6. 业务技能与评测集；
7. DeerFlow 配置与依赖锁定（锁定版本，升级前跑回归）。

**不用**：DeerFlow 的 Gateway、Web UI、IM 渠道、定时任务、Internal Auth、PAT、HITL 确认（业务审核统一走审批中心）、**bash、文件读写工具、代码沙箱、bash 子智能体、技能自我进化**（第 10.9 节）。

### 10.7 部署形态（内网单台服务器，一个法人，不做多租户）

- 一台内网服务器上运行：
  - CrossERP API 进程；
  - CrossERP 后台 worker 进程（后台任务 + 定时任务调度）；
  - **CrossERP agent worker 进程**（独立 venv，内含 DeerFlow SDK；v4 起与后台 worker 分开）；
  - MySQL；
  - 可选的 Nginx（只做 CrossERP 前端和反向代理）。
- **不部署 DeerFlow 服务，不装 Docker**。DeerFlow 以库的形式装在 agent worker 的 venv 里；它的数据目录（sqlite checkpoint、记忆、线程文件）放在 worker 专用目录，并纳入备份。
- 宿主机 bash 保持关闭；技能和 MCP 只从仓库内受控目录加载，只允许 HTTP 方式的 MCP（stdio 方式会启动本地进程，等于执行代码，禁用）；DeerFlow 的配置修改接口（`update_mcp_config`、`install_skill` 等）不向用户和 agent 开放。
- v3 写的「将来需要代码执行时再引入 Docker 沙箱」**删除**：按 maken 第 8 条，以后也不让 AI 执行代码，脚本库走注册函数（第 10.9 节）。


### 10.8 模型配置：兼容 OpenAI，前端填写，运行时交给 DeerFlowClient（v4，maken 第 6 条）

**核实结果**（DeerFlow 主干 commit `2a97ec3`，代码阅读，未运行；路径前缀同第 10 章开头）：

| 问题 | 结论 | 依据 |
|---|---|---|
| `config.yaml` 怎么配 OpenAI 兼容模型 | `models:` 下每项写 `name`、`use: langchain_openai:ChatOpenAI`、`model`、`api_key`、`base_url`（可选 `request_timeout`、`max_retries`、`max_tokens`、`temperature`、`supports_vision` 等）。官方示例里 llama.cpp、Novita、StepFun、MiniMax、Gemini 的 OpenAI 兼容端点都是这种写法 | `config.example.yaml` L302-313（OpenAI 示例）、L371-392（llama.cpp：`use: langchain_openai:ChatOpenAI` + `base_url: http://localhost:8080/v1`）、L525-533（Novita） |
| 密钥怎么写进配置 | 任何字段都可以写成 `$环境变量名`，加载时用 `os.getenv` 解析；变量不存在就报错 | `config.example.yaml` L15；`backend/packages/harness/deerflow/config/app_config.py` L647-665（`resolve_env_variables`） |
| `use` 是怎么生效的 | 工厂按 `use` 反射加载类；`langchain_openai:ChatOpenAI` 会换成 DeerFlow 的 `GuardedChatOpenAI`；其余字段作为构造参数传入 | `deerflow/models/factory.py` L542（`create_chat_model`）、L576-578 |
| DeerFlow 自己有没有「前端填密钥」 | **有**：Gateway 的 managed models（管理员在页面上维护共享模型，默认 provider 为 `openai-compatible`，字段 `base_url`、`api_key`、`model`）。做法：密钥用 `SecretStr`；列表只返回 `has_api_key`，不回显密钥；拒绝把掩码 `****` 当密钥保存；更新时不填密钥就保留原值；校验错误不回显请求体；目录用 Fernet 加密存在运行目录，密钥文件单独存放；加载配置时合并进模型清单 | `backend/app/gateway/routers/managed_models.py` L1（「Credentials never leave the server」）、L23-36、L114、L156；`deerflow/config/managed_models.py` L37-51、L66-67、L89-95、L159、L168-184、L256-273；`app_config.py` L843-845 |
| 嵌入的 client 什么时候读模型配置 | `DeerFlowClient` 构造时加载并缓存配置（`self._app_config`），之后改配置不会自动生效，需要新建 client（`reset_agent()` 只重建智能体，不重读配置） | `deerflow/client.py` L248-250、L282-292 |

**CrossERP 的做法**：
1. **前端「模型设置」页**（原 G17 页改名）：三个必填项 `baseUrl`、`model`、`apiKey`，可选 `temperature`、`maxTokens`；一个「测试连通」按钮。默认只有管理员能改（`agent_tool:write`，仅真人）；一家公司一份配置。
2. **接口**：
   - `GET /agent/model-config`：返回 `baseUrl`、`model`、`hasApiKey`，**永不返回密钥**；
   - `PUT /agent/model-config`：`apiKey` 只写；留空表示保留原值；拒绝掩码字符（借鉴 DeerFlow）；
   - `POST /agent/model-config/test`：用一句固定提示调用一次，只返回成功或失败原因。
3. **存储**：`apiKey` 用 AES-256-GCM 加密后存在 MySQL 的 `ModelConfig.apiKeyCiphertext`。主密钥放在服务器的环境变量或权限 600 的文件里，不进数据库、不进代码仓库。
4. **不写日志**：这个接口的请求体不进访问日志；操作日志里只记「API Key 已修改」；校验错误不回显请求体；LLM 调用记录不保存请求头。
5. **运行时交给 DeerFlowClient**（推荐方式）：
   - CrossERP 自带一份 `config/deerflow.yaml`，里面只有一个模型项，值全部写成环境变量引用：
     ```yaml
     models:
       - name: crosserp-default
         use: langchain_openai:ChatOpenAI
         model: $CROSSERP_LLM_MODEL
         base_url: $CROSSERP_LLM_BASE_URL
         api_key: $CROSSERP_LLM_API_KEY
     ```
   - agent worker 启动时，从 MySQL 读出配置并解密，只写进**本进程**的环境变量，然后构造 `DeerFlowClient(config_path="config/deerflow.yaml", …)`。密钥不落盘。
   - 管理员保存新配置后，发出 `model_config.updated` 事件。worker 收到后，等手上的对话跑完，再用新配置重建 client（worker 是独立进程，也可以直接平滑重启）。
   - 因为 bash 和文件工具全部关闭（第 10.9 节），AI 无法读取进程环境变量。
   - 备选方案：直接写入 DeerFlow 的 managed models 存储。缺点是密钥要在 CrossERP 和 DeerFlow 两处各存一份，所以不推荐。
6. **预算与降级**沿用现有设计：调用失败或预算达到 80% 时自动进入降级模式。

未核实：没有实际调用过任何 OpenAI 兼容端点；不同厂商兼容端点的工具调用和流式差异，以 DeerFlow 的官方示例为准，接入时逐个测试。


### 10.9 禁止 AI 执行代码（v4，maken 第 8 条）

**规则**：AI 不能执行任何代码。不开 bash，不开代码沙箱，不装 Docker。以后如果做脚本库，脚本只能以「注册过的功能函数」或「MCP 工具」的形式执行，并且同样走权限检查和风险分级。

**在 DeerFlow 里怎么关**（代码阅读，未运行）：

| 关什么 | 怎么关 | 依据 |
|---|---|---|
| bash 工具 | `config.yaml` 的 `tools:` 里不写 `bash`（`group: bash`）。另外保持 `sandbox.use: deerflow.sandbox.local:LocalSandboxProvider` + `allow_host_bash: false`，这样即使误配了 bash 工具也会被过滤。**注意**：换成非 Local 的沙箱提供者时，DeerFlow 会默认允许 bash，所以不能换 | `config.example.yaml` L1402-1406、L1751-1756；`deerflow/sandbox/security.py` L35-45；`deerflow/tools/tools.py` L124-140 |
| 文件读写工具 | `tools:` 里不写 `ls / read_file / glob / grep / write_file / str_replace`（`group: file:read`、`file:write`） | `config.example.yaml` L1374-1398 |
| 沙箱段 | DeerFlow 要求必须有 `sandbox` 配置段（没有默认值），所以保留 Local 提供者；它只是一个空壳，不执行任何东西，也**不需要 Docker** | `app_config.py` L277 |
| bash 子智能体 | 宿主机 bash 关闭时，内置的 `bash` 子智能体会被自动隐藏。但取不到配置时 DeerFlow 会退回「全部暴露」，所以 CrossERP 的守卫中间件再加一道白名单：只允许 `general-purpose` 子智能体 | `deerflow/subagents/builtins/__init__.py` L12-15；`deerflow/subagents/registry.py` L250-258 |
| 技能自我进化 | `skill_evolution.enabled: false`，否则会给 agent 加上 `skill_manage` 工具（可以写技能文件） | `deerflow/tools/tools.py` L249-253 |
| stdio MCP | 不配置 stdio 方式的 MCP 服务器（它会启动本地进程）；只允许 CrossERP 登记的 HTTP MCP | `backend/docs/MCP_SERVER.md` |
| 其余工具 | 守卫中间件只放行白名单：5 个 `crosserp_*` 工具、管理员登记的联网检索，以及 DeerFlow 内置的非执行类工具（澄清提问、展示文件、子智能体任务） | `deerflow/tools/tools.py` L36-44（内置工具清单） |

**以后的脚本库**（预留设计，首期不做）：
- 脚本由开发者编写、代码评审后随版本发布，登记成 `RegisteredFunction`。清单里写明输入输出 JSON Schema、权限点和风险级别。
- 每个函数作为一个实体动作（或 MCP 工具）暴露，经 `ActionDispatcher` 执行：权限、数据范围、风险分级、审批规则、日志和网页完全一样。
- AI 只能**调用**登记过的函数，不能上传、修改或临时生成脚本。
- 扩展点接口见第 4.11 节。

---

## 11. 数据库：正式环境以 MySQL 为主（v3，maken 第 7 条）

**结论**：正式环境用 **MySQL 8.4 LTS**（或 9.7 LTS），本机演示保留 SQLite，PostgreSQL 降为备选。现有后端已经做过三库兼容（ADR 0004，迁移里已有 MySQL 专用写法，例如 `MEDIUMTEXT`），所以切到 MySQL 为主不需要改架构。下面列出设计中在 MySQL 上需要注意的地方，以及在什么条件下必须换 PostgreSQL。

**版本**：MySQL 8.0 已于 2026-04 结束支持，Oracle 建议升级到 8.4 LTS 或 9.7 LTS（<https://www.mysql.com/support/eol-notice.html>）。8.4 LTS 的 Premier 支持到 2029-04，Extended 支持到 2032-04（<https://endoflife.date/mysql>）。**不要新装 8.0**。

### 11.1 设计在 MySQL 上的坑与对策

下表「核实」一列的依据是 MySQL 8.4 官方手册，2026-11-11 抓取原文确认了关键句。

| 设计点 | MySQL 上的情况 | 对策 | 依据 |
|---|---|---|---|
| **JSON 字段**：实体扩展属性、`EntityVersion.diff`、`RawRecord`、孪生状态、推演副本 | 有原生 JSON 类型，但**没有 PostgreSQL 那样的 GIN 通用索引**。只能用「函数索引」或「生成列 + 索引」索引单个路径，数组用多值索引 | 需要查询或过滤的字段**做成普通列**，例如实体 ID、状态、店铺、日期、金额。JSON 只存「整体读写」的内容（差异、原件、快照）。确实要按 JSON 路径查时，建函数索引或多值索引 | <https://dev.mysql.com/doc/refman/8.4/en/json.html>；<https://dev.mysql.com/doc/refman/8.4/en/create-index.html>（Functional Key Parts、Multi-Valued Indexes） |
| **递归查询**：角色继承、部门树、类目树、溯源图、组合装 | 支持 `WITH RECURSIVE`；`cte_max_recursion_depth` **默认 1000 层**，超过会报错 | 层级深度远小于 1000，可以直接用。溯源图在应用层逐层展开并限制最大深度（演示默认 20 层）；角色继承在写入时检查有没有环 | <https://dev.mysql.com/doc/refman/8.4/en/with.html> |
| **事务隔离级别** | InnoDB **默认是 REPEATABLE READ**（PostgreSQL 默认 READ COMMITTED）。范围更新会加间隙锁或 next-key 锁，热点行上容易死锁 | 应用连接统一设成 **READ COMMITTED**。需要串行的地方用 `SELECT … FOR UPDATE` 显式加行锁，包括：库存余额与移动加权成本、会计期间状态、哈希链日志头 `audit_head`、单据编号。死锁自动重试 3 次。实体乐观锁（`version`）不变 | <https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html> |
| **任务队列 / outbox** | 支持 `FOR UPDATE SKIP LOCKED`；没有 PostgreSQL 的 LISTEN/NOTIFY | worker 轮询任务表和 outbox，用 `SKIP LOCKED` 领取任务；轮询间隔 1–2 秒（演示默认值） | <https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html> |
| **孪生快照与历史**：`TwinSnapshot`、`EntityVersion`、按时点回看 | MySQL **没有系统版本表**（时态表）。分区表**不支持外键** | 时点回看用「版本表 +（实体类型, 实体 ID, 生效时间）复合索引」实现。快照内容存压缩 JSON 加哈希，大快照可以按「快照 ID + 分片」拆行。数据量大了以后，`EntityVersion`、`audit_log`、`run_event` 这类只追加表可以按月分区；这些表**不建外键**，由应用保证引用正确，现在的哈希链本来就不依赖外键 | <https://dev.mysql.com/doc/refman/8.4/en/partitioning-limitations.html> |
| **向量检索**：知识库语义检索 | MySQL 9.x 有 `VECTOR` 类型，但计算距离的 `DISTANCE()` **只在 HeatWave on OCI 和 MySQL AI 里提供，社区版和商业版都没有**；8.4 没有向量类型 | 首期知识检索用 **MySQL 全文索引 + ngram 分词**（支持中文），再加上实体链接和关键词。需要语义检索时，可以把向量放在进程内的嵌入式库（例如 DeerFlow 依赖里已有的 duckdb，是否适用未核实），或单独的向量服务（RAGFlow，DeerFlow 已支持）；也可以只在知识库这一块用 PostgreSQL + pgvector。**这是最可能逼你换库的一点**，见 11.3 | <https://dev.mysql.com/doc/refman/9.5/en/vector-functions.html>（原文：「DISTANCE() is available only for users of MySQL HeatWave on OCI and MySQL AI; it is not included in MySQL Commercial or Community distributions」）；<https://dev.mysql.com/doc/refman/8.4/en/fulltext-search-ngram.html> |
| **DDL 不在事务里** | `CREATE/ALTER TABLE` 会隐式提交，迁移中途失败时**不能整体回滚** | 每个 Alembic 迁移只做一件事，并写好 downgrade；上线前先在备份库上演练；大表改结构用在线 DDL（`ALGORITHM=INSTANT/INPLACE`）。现有迁移 0015、0018、0019 已经按 MySQL 处理过 | <https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html> |
| 部分索引（`WHERE` 条件唯一） | MySQL 不支持 | 用生成列配合唯一索引实现，例如「每个 SKU 只能有一条生效成本期间」 | 推断（MySQL 没有部分索引语法） |
| 金额 | `DECIMAL(20,4)` 或 `BIGINT` 万分位，与现有 `Money4` 一致 | 不变 | ADR 0004 |
| 字符集与时间 | 需要 `utf8mb4` + `utf8mb4_0900_ai_ci`；`DATETIME` 不带时区 | 一律存 UTC（现有 `UtcDateTime`）；连接设 `time_zone='+00:00'` | 推断 |

### 11.2 DeerFlow 的 checkpoint 在 MySQL 上的情况

- **DeerFlow 内置的 checkpointer 和数据库后端只支持 memory、sqlite、postgres**，不支持 MySQL。来源：
  - `deerflow/runtime/checkpointer/provider.py` L6（「Supported backends: memory, sqlite, postgres」）；
  - `deerflow/config/database_config.py` L144（`backend: Literal["memory","sqlite","postgres"]`）；
  - `config.example.yaml` L2679-2773。
- 嵌入模式可以传入任意 LangGraph checkpointer 实例（`client.py` L214、L231）。PyPI 上有社区包 `langgraph-checkpoint-mysql` 3.0.0（作者 Theodore Ni，<https://github.com/tjni/langgraph-checkpoint-mysql>，**非官方**）。和 DeerFlow 一起试解析能装上（解析到 langgraph-checkpoint 4.3.1），但**能否在 DeerFlow 的 checkpoint 模式检查（`ensure_checkpoint_mode_compatible`）和 delta 模式下正常工作，未核实**。
- **建议**：DeerFlow 的 checkpoint 用 **sqlite 文件**，放在 worker 数据目录（DeerFlow 默认就是这样；单台服务器够用）。它只保存对话过程的中间状态，**业务事实全在 MySQL**；对话的最终记录也由 CrossERP 写进自己的 MySQL 表。这样 DeerFlow 不需要 MySQL 支持，也不需要 PostgreSQL。将来 agent worker 要多台部署时，再评估 MySQL checkpointer，或者只给 DeerFlow 单独配一个 PostgreSQL。

### 11.3 什么情况下必须换 PostgreSQL

满足以下**任一条**才换，否则一直用 MySQL：
1. 知识库要做**大规模语义检索**（例如超过几十万段落、要求毫秒级近邻检索），而且不接受外挂向量服务或嵌入式向量库。这种情况下，可以只把知识库换成 PostgreSQL + pgvector，业务库仍然用 MySQL。
2. agent worker 要**多台横向扩展**，并且要使用 DeerFlow 官方支持的共享 checkpoint 或 Gateway 模式（它们只支持 PostgreSQL），而社区 MySQL checkpointer 验证不通过。
3. 出现大量需要在 JSON 内部任意字段上做复杂查询的报表需求，用生成列或函数索引无法满足（目前的设计没有这种需求）。
4. 要求迁移脚本整体事务回滚（事务性 DDL）作为上线硬性条件。

以下情况**不需要**换库：递归查询（MySQL 8.4 支持）、任务队列（`SKIP LOCKED`）、乐观锁、哈希链、按时点回看（版本表实现）、单台服务器上的 DeerFlow checkpoint（sqlite 文件）。

---

## 12. 已决定与待拍板

### 12.1 已决定

**v3 的 13 条（maken 2026-11-11 第一次回复）**：

| # | 事项 | 决定 | 落到哪里 |
|---|---|---|---|
| 1 | 后台定时任务 | **CrossERP 自己调度**，每次运行以委托人当时的权限自动签发任务通行证 | 第 10.3 节第 6 点；4.10 |
| 2 | 子智能体权限 | **否定「首期只读」**：子智能体与主智能体同样有执行权，同一委托、同一风险分级 | 第 10.2、10.4 节 |
| 3 | 孪生偏差与清洗问题由谁处理 | **agent 先处理，处理不了转交上传这批数据的人**；改账的结论仍须人工确认 | 第 9.3、9.5 节；2 个 `escalate` 接口 |
| 4 | 薪资、合同等敏感知识空间 | **同样由 AI 整理**；只读发起者或管理员有权看的来源，产出继承原空间权限，不跨空间 | 第 9.6 节；`POST /kb/compile-runs` |
| 5 | agent 执行权与通行证 | agent 有执行权，内部分级；通行证单张最长 24 小时，遇到登出、切换账号、权限变化、停用、关闭 AI 立即作废（v4 改为全自动、用户无感） | 第 10.4、10.5 节；4.4 |
| 6 | 技术栈 | 沿用现有 Python 后端 | 第 2.1 节 |
| 7 | 数据库 | 正式环境**以 MySQL 为主**，必要时才换 PostgreSQL（v4 再次确认） | 第 11 章 |
| 8 | 部署 | **内网服务器，一个法人，不做多租户** | 第 10.7 节；第 7 节「准则与主体」 |
| 9 | 平台接入顺序 | 文件导入 → Amazon SP-API → Shopify → 领星 | 第 8.1 节 |
| 10 | 对外对接与审批 | 外部账套**先金蝶、再用友、其次其他**；审批**先在平台内**，IM 后期；**审批不设金额上限** | 第 4.6、4.11、7、8.1 节 |
| 11 | 最后一期 | 人事、行政、客户（CRM）、广告放在 P5 | 第 8.1 节 |
| 12 | DeerFlow 部署形态 | **只用 SDK，不单独部署** | 第 10.0 节 |
| 13 | 契约调整 | 同意第 6 节 27 处调整 | 第 6 节 |

**v4 新增（maken 2026-11-11 第二次回复）**：

| # | 事项 | 决定 | 落到哪里 |
|---|---|---|---|
| 14 | agent 运行方式 | 智能体单独跑在一个 **worker 进程**里，用**独立的 Python 环境** | 第 10.1、10.7 节；4.10 |
| 15 | 风险分级口径 | **只按会不会改数据分级**；只读动作（含对账、利润、凭证、余额、报表等钱和账的查询）全部归只读级，AI 直接用；对账计算/匹配/差异分析属只读或低风险，只有生成凭证、调账才受「最多到起草、待审」限制 | 第 4.4、10.4 节；36 个接口改级 |
| 16 | 中风险限额 | **取消次数限额**；保留可撤销和事后通知，通知只进每日一条站内摘要 | 第 4.4、4.11、10.5 节 |
| 17 | 通行证 | **用户无感**：系统自动签发、静默续期、自动作废；删除「我的通行证」页面和人工作废入口；删除 2 小时空闲挂起；按「傻瓜式」原则清理增加负担的设计（清单见 12.3） | 第 10.5 节；删除 2 个接口 |
| 18 | 审批规则 | 审批人从流程配置解析：**配置了就必须审**（法人/老大也一样），自己不能审自己的单；**没配置或解析不到可用账号就免审直接生效**，日志记「无审批人，直接生效」；反结账同此规则；**单人模式取消** | 第 4.6 节；`GET /workflow/rules/resolve` |
| 19 | AI 发起、无可用审批人 | AI 发起的高风险或钱账动作没有可用审批人时，**退回发起它的本人确认，确认后才生效，并留痕**（maken：「这个设计是良好的」） | 第 4.6 节；`POST /approvals/{id}/initiator-confirm` |
| 20 | 模型 | **兼容 OpenAI**（baseUrl、apiKey、model），前端自己填；apiKey 加密存储、不回显、不进日志；参考 DeerFlow 的做法 | 第 10.8 节；`/agent/model-config*` |
| 21 | 代码执行 | **禁止 AI 执行代码**：关闭 bash 和沙箱，不装 Docker；以后的脚本库只能以注册函数或 MCP 工具执行，同样走权限和风险分级 | 第 10.9 节 |
| 22 | IM 与扩展 | IM 审批延后，先做平台；审批、通知、平台接入、外部账套都用**可插拔适配器**，接口约定写清楚 | 第 4.11 节 |
| 23 | llm_wiki | 只借鉴思路，不复制代码（GPL-3.0） | 第 9.7 节 |

**按第 18 条推导出的默认做法（不同意可推翻）**：
- 知识页发布与审批规则对齐：空间配置了审核人就由审核人发布；没配置时，AI 整理后直接发布，并留痕「无审核人，直接发布」。这替代了 v3 待拍板的「低风险知识空间是否允许 AI 直接发布」。
- 配置的审批人恰好是提交人本人、排除后没有别人时，按「解析不到可用账号」处理：人发起的单直接生效并留痕（原因码 `only_self`），AI 发起的退回本人确认。

### 12.2 仍待拍板

1. **会计口径**（沿用 v1）：科目编码、汇兑损益是否冲回、退税率、会计期间按北京时间自然月。确认前一律用演示默认值。
2. **平台账号与权限**：实际在用的平台和店铺清单；是否已有 SP-API 开发者资格、Shopify 和领星的 API 权限（未核实）。第 5 条孪生同步频率也取决于这一条。
3. **月度 LLM 预算**：模型由用户在前端自己填，只剩每月预算上限和告警阈值要定（演示默认：到 80% 自动降级）。
4. **DeerFlow 版本锁定**：建议锁定正式标签 `v2.2.0`。但本次核实的是主干 2.3.0-dev，`v2.2.0` 是否包含相同能力（`authz_attributes` 传递、`middlewares` 参数、managed models 等）**未核实**；另一种做法是锁定一个主干 commit。
5. **孪生同步频率**：FBA 库存每日、物流每 6 小时、银行流水每日，都是演示默认值，取决于第 2 条。
6. **实体目录的源头**：以 `entities.txt`（将来改成各模块 manifest）为唯一源头生成 OpenAPI、工具和前端类型（建议）；或者以代码模型为准反向生成。
7. **推演转草稿**：建议任何有推演权限的人都能把选中动作转成草稿，每条按原动作的权限和风险分级重新校验。是否需要限定只有主管才能操作？
8. **中风险清单复核**（可选）：74 个接口的具体条目（第 5 节 AI 列标为「中风险」的行），次数限额已取消，只需要看有没有该升级或降级的。
9. **IM 渠道**：后期先接飞书还是企业微信（不急）。

### 12.3 v4 按「傻瓜式、降低使用难度」删改的设计

| # | 原设计（v3） | v4 处理 | 结果 |
|---|---|---|---|
| 1 | 「我的通行证」页面，可一键作废 | **删除**页面和作废接口 | 用户不需要知道通行证存在 |
| 2 | 连续 2 小时无工具调用，通行证挂起 | **删除**；会话活跃时后台静默续期，到 24 小时前自动换新 | 对话不会被打断 |
| 3 | 权限变化后令牌失效，返回 401 `PERMISSIONS_CHANGED` | 旧通行证照样立即作废，但下次发消息时**按新权限静默重新签发** | 不报错、不用重新登录 |
| 4 | 中风险按人按日 50 次、每小时 20 次限额 | **删除** | 不会做到一半被卡 |
| 5 | 低风险有日次数上限 | **删除** | 同上 |
| 6 | 异常时自动挂起通行证，并通知本人和管理员 | 只写安全日志、只通知管理员 | 普通用户不受打扰 |
| 7 | 中风险动作逐条或每日通知被代表人 | 只发**每天一条站内摘要**，每条可一键撤销；不弹窗、不推送；可以关掉 | 通知少而短 |
| 8 | 单人模式与「不能自批」冲突，小团队可能没人能审 | 没有可用审批人时**直接生效并留痕**；AI 发起的退回本人确认 | 3 人团队也不会被审批卡住 |
| 9 | 提交后才知道走谁审批 | 新增 `GET /workflow/rules/resolve`，提交按钮旁直接显示「由谁审批 / 提交即生效 / 需你确认」 | 不用猜 |
| 10 | 流程模板需要先配好审批人 | 预置模板审批人默认留空；配了才生效 | 装好就能用 |
| 11 | 处理对账差异属高风险，须人工审核，且必须手填原因 | 改为中风险，AI 预填原因，人一键确认或直接由 AI 处理（可撤销） | 少一道审核 |
| 12 | 权限、日志、薪资等只读查询 AI 不能用 | 只读全部开放（按被代表人权限） | 能直接问 AI「为什么我看不到某个菜单」「这个月工资批次的状态」 |
| 13 | 配模型要改 `config.yaml` 或部署 DeerFlow Gateway；「DeerFlow 接入」页要填 Gateway 地址、MCP Token 名称 | 「模型设置」页只填 3 项，加一个测试按钮 | 不用懂部署 |
| 14 | 知识页一律由人审核后发布 | 空间没配审核人时 AI 直接发布并留痕 | 小团队不用专人审稿 |
| 15 | 清洗问题、孪生偏差、对账差异的人工处理要手写原因 | AI 预先填好原因和依据，人可以直接确认 | 少打字 |
| 16 | 登出时要求前端调用取消接口 | 服务端按会话自动停止，前端不需要额外调用 | 少一个出错点 |
| 17 | 新渠道、新平台、新账套要手写配置 | 适配器自带配置结构，设置页自动生成表单 | 管理员只填必要项 |

**保留的安全底线**（不增加普通用户的操作）：每次调用按当前权限重算；登出、切换账号、权限变化、停用、关闭 AI 时立即作废；改账的动作 AI 最多到起草、待审；不能自批；全程留痕。

## 13. 推断与未核实

- **推断**：
  - 本次新增的 235 个接口（第 5 节「来源=推断」，其中 v2 新增 55 个、v3 新增 2 个、v4 新增 2 个）；
  - 新包结构；
  - 审批「撤回」状态；
  - 新事件名，包括实体目录里自动生成的事件名；
  - 本机开发端口 8000；
  - 中风险与低风险清单的具体条目；
  - v4 默认值：「等待发起人确认」7 天未确认自动撤回；agent worker 同时运行 4 个对话；outbox 重试 3 次；每日摘要的发送时间；预置流程模板审批人留空；
  - 「配置的审批人就是提交人本人」按「解析不到可用账号」处理（第 12.1 节推导项）；
  - 模型密钥用 AES-256-GCM、主密钥放服务器环境变量或 600 权限文件；
  - 会计期间按北京时间切分；
  - `landed_cost_voucher:create` 新权限点；
  - 实体属性只列了关键字段，其余以前端 `src/types` 为准；
  - 状态机中标注「推断」的触发关系；
  - 孪生同步来源与频率；
  - 通行证静默续期的具体节奏（演示默认：每次消息或工具调用时刷新，距 24 小时上限 1 小时内换新）；
  - agent worker 进程与独立 venv 的划分（两套 venv 共用 CrossERP 领域包的打包方式需实现时确定）；
  - MySQL 连接参数（READ COMMITTED、UTC 时区）；
  - 部分索引用生成列替代的写法；
  - 孪生纠偏动作的权限点（`/twin/drifts/{id}/resolve` 暂用 `stock_reconciliation:create`，资金类偏差实现时按偏差类型映射到财务动作）。
- **未核实**：
  - v4 模型注入方式（worker 进程环境变量 + `$VAR` 引用）与关闭 bash/文件工具后的实际行为，均只读了代码，没有运行；任何 OpenAI 兼容端点都没有实际调用；
  - DeerFlow 嵌入模式**没有实际安装运行**：结论全部来自主干源码和文档；git 依赖的安装写法没有实测；`v2.2.0` 标签是否具备相同能力；子智能体继承 `authz_attributes` 只读了代码，没有跑测试；守卫中间件能否在工具调用前终止本轮，是按 LangChain AgentMiddleware 机制推断的；
  - 社区包 `langgraph-checkpoint-mysql` 与 DeerFlow checkpoint 模式能否兼容；
  - duckdb 能否胜任知识库向量检索；
  - 飞书、企业微信、钉钉开放平台的具体接口名；
  - 用友对接方式；
  - Amazon SP-API、Shopify、领星的可用权限；
  - 积加、马帮的角色设计；
  - 会计档案保留年限；
  - 1405/1406 编号以公司科目表为准；
  - ISO/IEC 30173、ISO 23247 的正文（只读了官方摘要）；
  - llm_wiki 的实际运行效果（只读了代码和 README）。
- **统计口径**：
  - 页面覆盖率按 `pageCatalog` 的 238 个页面 ID 计算。A02「无权限」和 A03「404」是纯说明页，不计入分母；
  - 166 个实体类型中包含 13 个只读投影（view），列在目录里只是为了给查询类接口找到归属；
  - 前端函数对接口的映射：对共享视图（gap-a/b/c/d/e、智能体模块）按页面人工指定，其余由脚本根据页面实际 import 的 service 函数推出；
  - 每期「累计可接真实数据的页面」按「该页面用到的所有接口都已上线」计算，偏保守。例如补货页 I13 用到了推演接口（P3），所以按 P3 才计入；实际上补货功能在 P2 就能用；
  - 生成脚本和中间数据在 box `/workspace/crosserp-backend-design/work/`（不在仓库）（v2 章节源文件在 `work/v2/`，v3 在 `work/v3/`，v4 在 `work/v4/`）。

## 14. 修订记录

| 版本 | 日期 | 内容 |
|---|---|---|
| v1 | 2026-11-11 | 22 个模块、473 个接口、页面覆盖 236/236 |
| v2 | 2026-11-11 | 以实体为核心：实体目录（166 个实体类型、499 个动作）、数据进入链路、数字孪生与推演、知识编译；委托令牌；接入 DeerFlow 2.0（Gateway + MCP 方案）；模块 22→25，接口 473→528 |
| v3 | 2026-11-11 | 按 maken 的 13 条拍板修订：<br>① DeerFlow 改为 **SDK 嵌入、不单独部署**（第 10.0 节核实）；<br>② 子智能体有执行权，通过 `authz_attributes` 加进程内回查保证身份（代码确认网络 secrets 不会传给子智能体）；<br>③ 风险分级 5 级，新增「中风险自动执行」73 个；<br>④ 通行证 24 小时，并补充风控；<br>⑤ 清洗问题和孪生偏差由 agent 先处理，处理不了转交上传人（新增 2 个接口，接口 528→530，动作 499→501）；<br>⑥ 所有知识空间由 AI 整理，按权限隔离；<br>⑦ 正式环境 MySQL 为主（第 11 章）；<br>⑧ 审批不设金额上限，IM 后期；外部账套金蝶→用友→其他；<br>⑨ 分期表与待拍板清单更新 |
| v4 | 2026-11-11 | 按 maken 第二次回复修订：<br>① agent 跑在独立 worker 进程、独立 Python 环境；<br>② 风险分级只看是否改数据：只读 224→258、低 34→37、中 73→74、高 57→56、危 142→104（36 个接口改级）；中风险取消次数限额，通知改为每日站内摘要；<br>③ 通行证全自动、用户无感：删除「我的通行证」页面、人工作废、2 小时空闲挂起；<br>④ 审批人从流程配置解析，无审批人直接生效并留痕，AI 发起的高风险/钱账动作无审批人时退回发起人本人确认（maken 已定），单人模式取消；<br>⑤ 模型兼容 OpenAI、前端填写、密钥加密不回显（核实 DeerFlow 模型配置与 managed models）；<br>⑥ 禁止 AI 执行代码；<br>⑦ 可插拔渠道与适配器接口约定；<br>⑧ 接口 530→529（删 3 增 2，3 个改名），动作 501→500；17 处减负设计见第 12.3 节；待拍板清单只留 9 项 |
