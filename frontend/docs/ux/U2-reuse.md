# U2 组件复用核对

## 复用的项目 / Vuexy 能力

- `src/pages/dashboard/index.vue`：继续使用已有 `/dashboard` 路由和默认 Vuexy layout，没有新增首页路由。
- `VRow`、`VCol`、`VCard`、`VCardItem`、`VList`、`VListItem`、`VChip`、`VAlert`、`VBtn`、`VAvatar`：使用 Vuetify/Vuexy 的栅格、卡片、列表和交互组件。
- `KpiCard`：复用项目已有的统计卡片包装，避免另造统计组件。
- `LoadingState`、`EmptyState`：复用项目现有加载与空状态。
- `shepherd.js` 13.0.3：复用已锁定依赖提供的 Tour、modal overlay、attachTo 和按钮能力；没有新增依赖。
- 现有 `fetchDashboard`、`fetchTodos`、`fetchApprovals`、`fetchScopedOrders`、`fetchScopedExpenses`、`fetchScopedContext`：首页只做权限 API 编排。

## 新增内容与理由

- `src/api/home.ts`：把首页需要的只读板块聚合为一个按权限容错的 API，避免页面直接依赖数据库或敏感记录。
- `src/components/tour/useOnboardingTour.ts`：集中管理 Shepherd 步骤、遮罩、跨页导航、角色可见菜单筛选和重新开始。
- `src/components/tour/onboarding.scss`：只补充 CrossERP 品牌化的引导卡片视觉，保留 Shepherd 的定位和遮罩机制。
- `src/pages/dashboard/index.vue`：将原空壳页面实现为个人工作台，内容包括待办、审批、权限范围内摘要和常用入口；AI 关闭时仍显示人工操作入口。
- `frontend/scripts/verify-u2.ts`：对本任务关键约束做静态守卫，尤其检查聚合 API 不出现工资/工资条读取。
