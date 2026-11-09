# 补齐批次 0：前端地基

本文件记录批次 0 的共享地基。新页面暂时统一注册为 `PlaceholderPage` 占位路由，页面实现由 A–E 批次各自完成。

## 地基内容

- `types/foundation.ts`：审批类型与多级规则（含 IM 门槛）、来源与建议、L0–L3 自主等级、AI 模式、文档链、部门、权限表、字段/数据范围、渠道插件。
- `config/permissions.ts` + `utils/permission-engine.ts`：权限点目录、角色多继承、允许/拒绝、用户例外和临时授权；显式拒绝优先，数据范围取并集后扣除拒绝，结果带来源说明。权限 key 采用 `DocType/模型:动作`，对齐 ERPNext Role Permission Manager / permlevel / User Permission / if_owner，以及 Odoo `res.groups` / `implied_ids` / `ir.model.access` / `ir.rule` / 字段 `groups`。AI 权限是被代表用户有效权限再取收窄集合。
- `stores/permissions.ts`、`stores/ai-mode.ts`：有效权限和 AI 总开关的 Pinia 状态，并持久化会话级设置。
- `mocks/services/foundation*`、`api/foundation.ts`：静态种子与将来的 `/api/v1` 函数。
- `AgentCard` 追加 `level`、`confidence`、`evidence`、`suggestionId`、`expiresAt`。
- 频道插件提供发消息、审批卡片、回调签名校验和身份绑定，内置飞书、企业微信、钉钉、邮件、Webhook。
- 表单校验统一经 vue-i18n；助手抽屉新消息自动滚到底部，输入区保持可见。

## 占位路由清单

### 批次 A

| 页面编号 | 路由 | 名称 | 默认阶段 |
|---|---|---|---|
| EX01 | ``/expense/claims`` | 报销单列表 | 现在做 |
| EX02 | ``/expense/claims/new`` | 新建报销 | 现在做 |
| EX03 | ``/expense/claims/:id`` | 报销详情 | 现在做 |
| EX04 | ``/expense/loans`` | 借款单 | 现在做 |
| EX05 | ``/expense/loans/:id`` | 借款详情 | 现在做 |
| EX06 | ``/expense/trips`` | 差旅申请 | v1.0 |
| EX07 | ``/expense/policies`` | 费用标准 | 现在做 |
| F23 | ``/finance/gl`` | 总账 / 明细账 | 现在做 |
| F24 | ``/finance/trial-balance`` | 科目余额表 | 现在做 |
| F25 | ``/finance/statements/income`` | 利润表 | 现在做 |
| F26 | ``/finance/statements/balance`` | 资产负债表 | 现在做 |
| F27 | ``/finance/statements/cashflow`` | 现金流量表 | v1.0 |
| F28 | ``/finance/period-close`` | 期末结账 | 现在做 |
| F29 | ``/finance/cogs`` | 成本结转 | 现在做 |
| F30 | ``/finance/budgets`` | 预算 | v1.0 |
| F31 | ``/finance/budgets/:id`` | 预算详情 | v1.0 |
| F32 | ``/finance/fx-revaluation`` | 汇兑损益 | v1.0 |
| F33 | ``/finance/tax/vat`` | VAT | v1.0 |
| F34 | ``/finance/tax/export-rebate`` | 出口退税 | 后期 |

### 批次 B

| 页面编号 | 路由 | 名称 | 默认阶段 |
|---|---|---|---|
| S09 | ``/procurement/rfqs`` | 询价单 | v1.0 |
| S10 | ``/procurement/rfqs/:id`` | 询价比价 | v1.0 |
| S11 | ``/procurement/contracts`` | 采购合同 | v1.0 |
| S12 | ``/procurement/contracts/:id`` | 合同详情 | v1.0 |
| S13 | ``/procurement/supplier-scores`` | 供应商评估 | v1.0 |
| I12 | ``/inventory/batches`` | 批次与效期 | v1.0 |
| I13 | ``/inventory/replenishment`` | 补货建议 | 现在做 |
| I14 | ``/inventory/transfers/:id`` | 调拨详情 | 现在做 |
| I15 | ``/inventory/counts/:id`` | 盘点详情 | 现在做 |
| W08 | ``/approvals/im-preview`` | IM 审批卡片预览 | v1.0 |
| INT01 | ``/integrations/import-wizard`` | 领星/赛狐导入向导 | 现在做 |
| INT02 | ``/integrations/sync-jobs`` | 平台同步 | v1.0 |
| INT03 | ``/integrations/kingdee`` | 金蝶导出设置 | v1.0 |
| INT04 | ``/integrations/erpnext`` | ERPNext 账套（可选） | 后期 |
| INT05 | ``/integrations/logs`` | 集成日志 | v1.0 |
| D05 | ``/dashboard/chain`` | 业务链追溯 | 现在做 |
| SYS19 | ``/account/channel-bindings`` | 我的渠道绑定 | v1.0 |
| SYS20 | ``/admin/im-approval`` | IM 审批设置 | v1.0 |
| SYS25 | ``/admin/channels`` | 通知渠道 | v1.0 |
| SYS26 | ``/admin/channels/new`` | 新增渠道 | v1.0 |

### 批次 C

| 页面编号 | 路由 | 名称 | 默认阶段 |
|---|---|---|---|
| W05 | ``/approvals/agent-suggestions`` | 智能体建议 | 现在做 |
| W06 | ``/approvals/cc`` | 抄送我的 | v1.0 |
| W07 | ``/approvals/rules`` | 审批规则与额度 | 现在做 |
| N01 | ``/notifications`` | 消息中心 | 现在做 |
| N02 | ``/notifications/subscriptions`` | 我的订阅 | v1.0 |
| RP01 | ``/reports`` | 报表中心 | 现在做 |
| RP02 | ``/reports/:id`` | 报表查看 | 现在做 |
| RP03 | ``/reports/builder`` | 自定义报表 | 后期 |
| U05 | ``/audit/ai`` | AI 操作日志 | 现在做 |
| U06 | ``/audit/ai/:id`` | 建议追溯 | 现在做 |
| U07 | ``/audit/alerts`` | 敏感操作告警 | v1.0 |
| U08 | ``/audit/retention`` | 日志保留与归档 | v1.0 |
| SYS14 | ``/admin/field-permissions`` | 字段权限 | 现在做 |
| SYS15 | ``/admin/data-scopes`` | 数据范围 | 现在做 |
| SYS16 | ``/admin/temp-grants`` | 临时授权 | v1.0 |
| SYS17 | ``/admin/access-reviews`` | 权限复核 | v1.0 |
| SYS21 | ``/admin/roles/:id`` | 角色详情 | 现在做 |
| SYS22 | ``/admin/permission-matrix`` | 权限矩阵 | 现在做 |
| SYS23 | ``/admin/effective-permissions`` | 有效权限查看 | 现在做 |
| SYS24 | ``/admin/permission-changes`` | 权限变更记录 | 现在做 |
| SYS18 | ``/admin/sod-rules`` | 职责分离规则 | 现在做 |

### 批次 D

| 页面编号 | 路由 | 名称 | 默认阶段 |
|---|---|---|---|
| HR01 | ``/hr/org`` | 组织架构 | 后期 |
| HR02 | ``/hr/employees`` | 员工档案 | 后期 |
| HR03 | ``/hr/employees/:id`` | 员工详情 | 后期 |
| HR04 | ``/hr/onboarding`` | 入职离职 | 后期 |
| HR05 | ``/hr/attendance`` | 考勤 | 后期 |
| HR06 | ``/hr/leave`` | 请假 | 后期 |
| HR07 | ``/hr/payroll`` | 薪资批次 | 后期 |
| HR08 | ``/hr/payroll/:id`` | 薪资批次详情 | 后期 |
| HR09 | ``/hr/payroll/:id/review`` | 薪资复核 | 后期 |
| HR10 | ``/hr/payroll/rules`` | 社保公积金与个税规则 | 后期 |
| HR11 | ``/hr/payroll/deductions`` | 专项附加扣除 | 后期 |
| HR12 | ``/hr/payslips`` | 我的工资条 | 后期 |
| AM01 | ``/office/contracts`` | 合同管理 | 后期 |
| AM02 | ``/office/assets`` | 固定资产 | 后期 |
| AM03 | ``/office/assets/:id`` | 资产详情 | 后期 |
| AM04 | ``/office/announcements`` | 公告 | 后期 |
| AM05 | ``/office/supplies`` | 办公用品 | 后期 |
| G18 | ``/agent/autonomy`` | 自主等级 | 现在做 |
| G19 | ``/agent/control`` | AI 总开关 | 现在做 |
| G20 | ``/agent/inbox`` | 票据收件箱 | 现在做 |
| G21 | ``/agent/alerts`` | 主动提醒 | 现在做 |
| G22 | ``/agent/trust`` | 可信度看板 | v1.0 |
| G23 | ``/agent/data-scope`` | AI 范围收窄（可选） | 现在做 |
| G24 | ``/agent/tools/:id`` | 工具详情与配置 | v1.0 |
| G25 | ``/agent/tools/new`` | 新增工具 | v1.0 |
| G26 | ``/agent/mcp-servers`` | MCP 服务器 | v1.0 |

### 批次 E

| 页面编号 | 路由 | 名称 | 默认阶段 |
|---|---|---|---|

## 共享文件约定

- A–E 只在 `pages.ts` 末尾对应批次块追加页面元数据；不要修改现有 128 页路由。
- 各批次页面内容统一复用 `components/biz/*`，真实接口接入前只通过 `src/api/*.ts` 假函数；不要在页面里写请求路径。
- i18n、权限种子和 mock 数据新增内容放在文件末尾的批次块，避免互相覆盖。
- 新单据状态采用 ERPNext `docstatus`（0 草稿、1 已提交、2 已取消）加业务 `status` 两层；旧页面状态值保持不变。
- 金额只由确定性代码计算，`MoneyText` 只展示；涉及钱、凭证、付款、薪资的智能体动作最高 L2，L3 仅限白名单低风险动作。
- `/agent/knowledge` 跳转到 `/kb` 留给批次 E。
