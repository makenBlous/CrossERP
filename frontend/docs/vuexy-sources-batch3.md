# 第 3 批页面来源记录

本批页面沿用 Vuexy full-version 的页面结构和本仓库共享组件；没有复制 Vuexy 源码。

| 页面 | 参考来源 |
| --- | --- |
| CRM dashboard | `pages/dashboards/crm.vue`、`views/dashboards/*`、`KpiCard` |
| 客户 / 客户详情 | `apps/ecommerce/customer/list`、`customer/details`、`apps/user/view` |
| 线索 / 商机看板 | `apps/kanban`、`views/apps/kanban` |
| 联系人 / 评价 / 用户列表 | `apps/user/list`、`apps/ecommerce/manage-review`、`ListPage` |
| 跟进日历 | `apps/calendar`、`AppDateTimePicker` / `VCalendar` |
| 售后工单 | `apps/email` / `apps/chat` 对话线程、`DetailPage` |
| 用户 / 用户详情 | `apps/user/list`、`apps/user/view/[id]` |
| 角色 / 权限 | `apps/roles`、`apps/permissions`、`AddEditRoleDialog`、`AddEditPermissionDialog` |
| 平台授权 / 通知 / 系统参数 | `pages/account-settings/[tab]` 的 Connections、Notification、Billing/Settings 结构 |
| 模块卡片 | `pages/cards/card-widgets.vue`、`CardStatisticsHorizontal` |
| 资料 / 密码 / Token / 会话 | `pages/account-settings/[tab]`、`pages/user-profile`、Security tab |

业务数据仍通过 `src/api/` 访问本地 mock 服务；金额只在服务层按万分位整数保存。
