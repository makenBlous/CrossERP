# 第 3 批页面来源记录

本批页面沿用 Vuexy full-version 的页面结构和本仓库共享组件；Vuexy 目录保持只读，没有直接修改。

| 页面 | 参考来源 |
| --- | --- |
| `/crm/dashboard` | `src/pages/dashboards/crm.vue`；`src/views/dashboards/crm/*`（统计卡与图表结构）；本仓库 `src/components/KpiCard.vue` |
| `/crm/accounts` | `src/pages/apps/ecommerce/customer/list.vue`；`src/components/biz/ListPage.vue` |
| `/crm/accounts/:id` | `src/pages/apps/ecommerce/customer/details.vue`；`src/pages/apps/user/view/[id].vue`；`src/components/biz/DetailPage.vue` |
| `/crm/leads` | `src/pages/apps/user/list.vue` 的列表筛选结构；`src/components/biz/ListPage.vue` |
| `/crm/leads/board` | `src/pages/apps/kanban.vue`；`src/views/apps/kanban/KanbanBoard.vue`、`KanbanItems.vue`、`KanbanCard.vue` |
| `/crm/opportunities` | `src/pages/apps/kanban.vue`；`src/views/apps/kanban/KanbanBoard.vue`、`KanbanCard.vue` |
| `/crm/contacts`、`/crm/contacts/:id` | `src/pages/apps/user/list.vue`、`src/pages/apps/user/view/[id].vue`；`src/components/biz/ListPage.vue`、`DetailPage.vue` |
| `/crm/activities` | `src/pages/apps/calendar.vue`；`src/views/apps/calendar/Calendar.vue`、`AppDateTimePicker` |
| `/crm/tickets`、`/crm/tickets/:id` | `src/pages/apps/email.vue`；`src/views/apps/chat/ChatLog.vue`；`src/components/biz/DetailPage.vue` |
| `/crm/reviews` | `src/pages/apps/ecommerce/manage-review.vue`；`src/views/apps/ecommerce/review/*`；`src/components/biz/ListPage.vue` |
| `/admin/users`、`/admin/users/:id` | `src/pages/apps/user/list.vue`、`src/pages/apps/user/view/[id].vue`；`src/views/apps/user/view/UserBioPanel.vue`、`UserTabAccount.vue`、`UserTabSecurity.vue` |
| `/admin/roles` | `src/pages/apps/roles.vue`；`src/views/apps/roles/RoleCards.vue`、`UserList.vue`；`src/components/dialogs/AddEditRoleDialog.vue`（扩展页面可见性矩阵） |
| `/admin/permissions` | `src/pages/apps/permissions.vue`；`src/components/dialogs/AddEditPermissionDialog.vue` |
| `/admin/stores` | `src/pages/apps/ecommerce/customer/list.vue` 的表格结构；`src/components/biz/ListPage.vue` |
| `/admin/integrations` | `src/views/pages/account-settings/AccountSettingsConnections.vue` |
| `/admin/modules` | `src/pages/cards/card-widgets.vue`；`src/components/KpiCard.vue` |
| `/admin/dicts` | `src/pages/apps/user/list.vue` 的筛选表格结构；`src/components/biz/ListPage.vue` |
| `/admin/notifications` | `src/views/pages/account-settings/AccountSettingsNotification.vue` |
| `/admin/settings` | `src/pages/apps/ecommerce/settings.vue`；`src/views/pages/account-settings/AccountSettingsBillingAndPlans.vue` 的页签结构 |
| `/account/profile` | `src/views/pages/account-settings/AccountSettingsAccount.vue`；`src/pages/user-profile.vue` |
| `/account/password`、`/account/tokens`、`/account/sessions` | `src/views/pages/account-settings/AccountSettingsSecurity.vue`（密码卡、API key、设备表） |

业务数据仍通过 `src/api/` 访问本地 mock 服务；金额只在服务层按万分位整数保存。
