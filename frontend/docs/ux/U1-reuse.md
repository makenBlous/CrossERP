# U1 组件复用核对

## 已复用

- `src/components/biz/ListPage.vue`：继续使用项目的列表页封装、筛选、分页、列设置、保存视图和 CSV 导出；新增 `actions` 插槽只负责把页面操作放进同一行标题区域。
- Vuexy/Vuetify 的 `VCard`、`VLayout`、`VNavigationDrawer`、`VMain`、`VBtn` 和响应式断点：经营日历仍使用现有布局组件，不引入新的 UI 库。
- `@fullcalendar/vue3` 与项目已经安装的 `dayGrid`、`timeGrid`、`list` 插件：桌面月视图保留，窄屏切换到列表视图，并使用 FullCalendar 的 `dayMaxEvents`/更多弹层处理事件密集日期。
- `vite-plugin-vue-meta-layouts` 的 `setupLayouts`：路由层统一包装有子路由的父页面，详情页继续复用同一个默认布局。

## 新增内容与理由

- 没有新增组件库、依赖或页面头组件。`ListPage` 的 `actions` 插槽是最小改动，可以让商品、库存、采购、物流和订单列表复用同一标题排版。
- 日历只增加页面级尺寸和响应式样式，用可用高度承载完整月视图；不缩放整页，也不裁剪最后一周。
