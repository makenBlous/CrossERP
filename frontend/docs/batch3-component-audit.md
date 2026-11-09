# 第 3 批组件复用审计

## 自写组件/区块与现有等价实现

| 自写组件/区块 | 现有等价组件(Vuexy/Vuetify/地基) | 处理（已替换/保留原因） |
|---|---|---|
| `AgentWorkspacePage` | `ListPage`、`DetailPage`、`VWindow`、`VTimeline` | 已替换；拆为 `src/views/agent/AgentListPage.vue`、`AgentDetailPage.vue`、`AgentSetupPage.vue`，页面目录只保留路由壳。 |
| 智能体定义卡片 | Vuexy roles 的 `VCard` + `VAvatar` + `VChip` | 已替换；直接使用 Vuetify/Vuexy 组合。 |
| 智能体工具权限矩阵 | Vuexy roles permission table + `VTable` | 已替换；复用 `VTable`、`VChip`、`VIcon`。 |
| 智能体运行/任务/知识库/评测/用量列表 | `ListPage`（Vuexy product/user list 薄封装） | 已替换；统一筛选、分页、列设置和 CSV。 |
| 智能体详情页 | `DetailPage` + user view `VTabs`/`VWindow` + `VTimeline` | 已替换；详情路由统一右侧审计轨迹。 |
| DeerFlow 配置向导 | Vuexy wizard / `VStepper` | 已替换；使用 `VStepper` 与只读连接卡。 |
| `AuditWorkspacePage` | `ListPage`、`FormPage`、`VTimeline`/`VTable` | 已替换；拆为审计列表、校验、导出和安全日志视图。 |
| 审计事件和安全事件表 | `ListPage` + `StatusChip`/`VChip` | 已替换；页面只调用 `src/api`。 |
| 审计导出表单 | `FormPage` + `AppTextField`/`AppSelect` | 已替换；保留导出 API 与下载行为。 |
| `ModuleTable` | `ListPage` | 已删除并迁移所有 CRM、后台、账户调用方。 |
| CRM 阶段看板 | Vuexy `views/apps/kanban` 的 FormKit `useDragAndDrop` | 已替换；迁移到 `src/views/crm/kanban/CrmKanbanBoard.vue`，数据仍来自 CRM API。 |
| `StatusChip`、`MoneyText`、`PermissionGate` | 项目业务地基组件 | 保留原因：承载项目状态字典、万分位金额展示和角色权限语义。 |
| 对话消息和建议卡 | Vuexy chat `ChatLog`/`ChatMessageForm` | 保留原因：已是跨全局助手与 `/agent/chat` 共用的适配层，写操作仍只提交审批建议。 |

## 页面与 Vuexy 来源

| 页面 | 改编自 Vuexy 文件 |
|---|---|
| `/crm/accounts`、`/crm/contacts`、`/crm/leads`、`/crm/tickets`、`/crm/reviews` | `pages/apps/user/list`、`pages/apps/invoice/list` 的 `VDataTableServer` 结构，经 `ListPage` 统一封装 |
| `/crm/leads/board`、`/crm/opportunities` | `pages/apps/kanban/index.vue`、`views/apps/kanban/KanbanItems.vue`、`KanbanCard.vue` |
| `/crm/*/:id` | `pages/apps/user/view` 的详情头、pill tabs 与右侧时间线 |
| `/crm/dashboard`、`/crm/activities` | `pages/dashboards/analytics` 卡片与 `pages/apps/calendar.vue` |
| `/admin/users`、`/admin/roles`、`/admin/permissions` | `pages/apps/user/list`、`views/apps/roles`、`components/dialogs/AddEditRoleDialog.vue` 的权限表 |
| `/admin/stores`、`/admin/integrations`、`/admin/modules`、`/admin/dicts`、`/admin/notifications`、`/admin/settings` | Vuexy `VCard`/`VDataTableServer` 设置页模式，经 `ListPage` 或 Vuetify 表单组合 |
| `/admin/users/:id` | `pages/apps/user/view` 的标签页详情 |
| `/account/profile`、`/account/password`、`/account/tokens`、`/account/sessions` | `pages/pages/user-profile`、`pages/pages/account-settings`、`pages/apps/user/list` |
| `/agent/definitions`、`/agent/tools` | `views/apps/roles` 的角色卡和 permission table |
| `/agent/definitions/:id`、`/agent/tasks/:id`、`/agent/runs/:id`、`/agent/knowledge/:id`、`/agent/evals/:id`、`/agent/usage/:id` | `pages/apps/user/view` 的 pill tabs、`DetailPage` 右侧时间线、Vuetify `VTimeline` |
| `/agent/runs`、`/agent/tasks`、`/agent/knowledge`、`/agent/evals`、`/agent/usage`、`/agent/threads`、`/agent/prompts` | `pages/apps/user/list`/`pages/apps/email` 列表模式，经 `ListPage` |
| `/agent/deerflow` | `pages/wizard-examples` 与 `components/dialogs/CreateAppDialog.vue` 的 `VStepper` |
| `/agent/chat` | `pages/apps/chat.vue`、`views/apps/chat/ChatLog.vue`、`ChatMessageForm.vue` |
| `/audit`、`/security-log` | `pages/apps/user/list` 的事件表与 `VChip` 状态 |
| `/audit/verify` | `VTimeline`/`VTable` 哈希链校验模式 |
| `/audit/export` | `pages/pages/misc` 表单与 ecommerce product add 的 `FormPage` 布局 |

## 路由检查

`src/config/pages.ts` 中 `/crm`、`/agent`、`/audit`、`/security-log`、`/admin`、`/account` 前缀的已实现页面均有对应 `.vue` 文件；本配置没有 `/llm` 路由。页面目录未再放置业务组件，因此 Vite 文件路由不会把审计或智能体组件误识别为路由。

所有页面继续通过 `src/api/*` 读取或提交 mock 数据；智能体写操作只调用审批服务，金额仍由服务层提供。
