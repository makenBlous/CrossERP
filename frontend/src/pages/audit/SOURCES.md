# 审计与安全页面来源

| 页面 | Vuexy full-version 来源 |
|---|---|
| `/audit` | `pages/apps/user/list` / `pages/tables/data-table.vue` 的筛选表格 |
| `/audit/verify` | `VTimeline` 与 `pages/apps/invoice/preview` 的只读详情区块 |
| `/audit/export` | `pages/wizard-examples` 的向导表单与下载动作 |
| `/security-log` | `pages/apps/user/list` 的事件表与 `VChip` 状态 |

页面使用项目自己的审计服务和 Vuetify 组件，没有复制商业模板源码。
