## 第3批（CRM/智能体/审计/设置）

第 3 批页面优先复用 Vuexy 与 Vuetify：列表统一使用 `ListPage`，详情统一使用 `DetailPage`、`VTabs`/`VWindow` 与 `VTimeline`，表单使用 `FormPage`/`FormDrawer`。智能体路由组件已移到 `src/views/agent/`，审计组件已移到 `src/views/audit/`，CRM 看板改编 Vuexy Kanban 的 FormKit 拖拽实现并放在 `src/views/crm/kanban/`。原 `ModuleTable`、`StageBoard` 和页面目录下的大型 workspace 组件已删除，页面仍只调用 `src/api/*`。完整逐页来源与处理记录见 `frontend/docs/batch3-component-audit.md`。
