# U1 接入说明

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](../前端开发规范.md) 和 [对接真实接口](../对接真实接口.md)。


本任务只修改 U1 文件所有权范围内的路由包装、列表页头部插槽、相关列表页模板和经营日历。没有修改以下公共文件：

- `src/config/pages.ts`
- `src/plugins/i18n/ui.ts`
- `package.json`、`pnpm-lock.yaml`
- 权限、授权、令牌、审批职责分离和身份相关文件

整合时无需新增 i18n key 或依赖：列表页继续使用已有文案，按钮通过 `ListPage` 的局部 `actions` 插槽渲染。路由修复保留原始 path/name，父路由和详情子路由都由默认布局包裹，因此无需改导航数据。

经营日历的窄屏策略是 `<768px` 使用 FullCalendar `listMonth`，桌面使用完整月视图；`dayMaxEvents` 只在桌面月视图启用，事件过多时由 FullCalendar 的更多弹层承载。

`finance/fx-rates.vue` 仍通过共享的 `FinanceTablePage` 展示。整合补丁为该共享视图增加了向后兼容的 `actions` 透传，汇率页把“新增月汇率”放入标题行；其他使用方未提供该插槽时保持原有布局和行为。
