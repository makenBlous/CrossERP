# 智能体页面来源

| 页面 | Vuexy full-version 来源 |
|---|---|
| `/agent/chat` | `pages/apps/chat.vue`、`views/apps/chat/ChatLog.vue`、消息输入条 |
| `/agent/definitions`、详情 | `pages/apps/roles` 的角色卡片与 `pages/apps/user/view/[id]` 的页签布局 |
| `/agent/tools` | `pages/apps/permissions` 的权限矩阵表 |
| `/agent/threads` | `pages/apps/email` 的邮件列表结构 |
| `/agent/tasks`、详情 | `pages/apps/kanban` 与 `views/apps/kanban` 的任务卡片、`VTimeline` |
| `/agent/runs`、详情 | `pages/apps/invoice/list` 的数据表与 `VTimeline` |
| `/agent/knowledge`、详情 | `pages/apps/academy` 的课程/文档列表与展开面板 |
| `/agent/prompts` | `pages/apps/roles` 的版本表与卡片布局 |
| `/agent/evals`、详情 | `pages/dashboards/analytics.vue` 的指标卡和 `pages/tables/data-table.vue` |
| `/agent/usage`、详情 | `pages/dashboards/analytics.vue` 的统计卡、进度条和图表布局 |
| `/agent/deerflow` | `pages/wizard-examples` 的步骤向导 |

页面只复用 Vuexy 的布局思路和 Vuetify 组件，没有复制商业模板源码。
