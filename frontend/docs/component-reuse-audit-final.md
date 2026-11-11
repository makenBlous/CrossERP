# 整合后整体组件复用审计

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](./前端开发规范.md) 和 [对接真实接口](./对接真实接口.md)。


审计范围：`3f325c0..HEAD` 中 `frontend/src` 的新增和修改页面、组件、视图，重点覆盖批次 A–E、UX U1–U3、首页、聊天、消息中心、凭证审批和本人工资条门控。

审计方式：只读检查 `git diff`、静态搜索和现有离线核验脚本；未启动开发服务器或常驻服务，未读取 `.env`、密钥、令牌或演示密码文件，未修改 `src` 代码和测试。

## 审计结果

| 编号 | 文件和行号 | 复用对象 | 结论 | 理由 |
| --- | --- | --- | --- | --- |
| R01 | `src/components/biz/ListPage.vue:465-501`；批次 A–E 各列表页 | `ListPage`、Vuexy `VDataTableServer`、`TablePagination` | 保留 | 列设置、筛选、保存视图、CSV、批量操作和行打开集中在一个列表地基中。新增列表页通过插槽提供业务列和动作，没有重复实现分页或筛选。 |
| R02 | `src/views/finance/FinanceTablePage.vue:46-78`；`src/pages/finance/fx-rates.vue:38-52` | `ListPage` 的 `actions` 插槽 | 保留 | 财务通用表格透传标题行动作；汇率页的新增动作已进入页头，符合 U1 的统一布局。 |
| R03 | `src/components/biz/DetailPage.vue:22-78`；`src/views/gap-b/GapBPage.vue:247-282`；`src/views/gap-c/GapCPage.vue:624-945`；`src/views/gap-d/BatchDPage.vue:476-663`；`src/views/knowledge/KnowledgePage.vue:371-542` | `DetailPage`、Vuexy 详情布局、`VTimeline` | 保留 | 批次视图将详情标题、状态、时间线和关联记录交给统一壳，业务内容保留在插槽中。没有发现重复的详情页双栏实现。 |
| R04 | `src/components/biz/ConfirmHost.vue:25-43`；`src/App.vue:27-29`；`src/components/biz/GapAPage.vue:1065-1103` | Vuexy `ConfirmDialog`；Vuetify `VDialog` | 保留 | 全局确认走 `ConfirmHost`。Gap A 弹窗展示匹配候选、金额和规则后再由人工确认，属于业务详情交互，不是重复的通用确认框。 |
| R05 | `src/components/biz/ScopedDataPreview.vue:83-165`；`src/pages/me/data-scope.vue:59-66`；`src/views/gap-c/GapCPage.vue:990-1001` | `ScopedDataPreview`；scoped read API | 保留 | 三张紧凑快照表由同一组件渲染，并展示 `shopId`、`ownerId`、`department` 和接口拒绝状态。它是当前主体数据范围的并排预览，不需要 `ListPage` 的分页、列设置或导出。 |
| R06 | `src/components/biz/AuditActorId.vue:1-13`；`src/views/audit/AuditListPage.vue:48-53`；`src/views/gap-c/GapCPage.vue:490-494` | `AuditActorId` | 保留 | 通用审计列表和 Gap C 的 `actorId` 都使用同一推断标记组件；`confirmerId` 是另一位确认人的稳定 ID，不是另一种 actor 展示实现。 |
| R07 | `src/components/biz/MoneyText.vue:1-29`；`src/views/gap-b/GapBPage.vue:324-328,388-397,854-860`；`src/views/gap-c/GapCPage.vue:482-488,1030-1034`；`src/views/gap-d/BatchDPage.vue:680-720,1153-1162,1303-1334`；`src/pages/finance/vouchers/[id].vue:155-181` | `MoneyText`、`utils/money` | 保留 | 金额列和详情金额统一经过 `MoneyText`，万分位数据由 API 返回，页面不重新计算。工资金额先由 `minorFromCents` 转换后再展示，符合统一口径。 |
| R08 | `src/components/biz/GapAPage.vue:121,606,682-701,736-745` | `MoneyText`、`utils/money` | 保留 | `displayMinor` 仅用于 `KpiCard` 的字符串属性和内联 `VAlert`，这两个位置无法直接嵌入 `MoneyText`；转换仍复用 `toDisplay` 和 `formatMoney`，没有另造金额算法。 |
| R09 | `src/components/chat/ChatThread.vue:1-85`；`src/components/biz/AssistantDrawer.vue:238-291`；`src/pages/agent/chat.vue:276-324` | `ChatThread`、`ChatLog`、`ChatMessageForm`、`ChatStatusLine` | 保留 | 浮动助手和智能体中心共用消息滚动区、气泡、输入条、加载/取消/重试状态；两处只保留各自的 AgentCard 和会话上下文。 |
| R10 | `src/components/chat/ChatComposer.vue:1-30`；`src/components/chat/ChatMessage.vue:1-23` | `ChatMessageForm`、`ChatLog` | 保留（兼容薄适配） | 两个文件只转发到既有聊天组件，当前没有重复绘制 UI。它们虽然没有本仓库页面直接引用，但注释明确其用途是兼容旧引用，暂不视为业务死代码。 |
| R11 | `src/components/tour/useOnboardingTour.ts:89-185`；`src/pages/dashboard/index.vue:16,214-229` | Shepherd Tour、现有导航 DOM | 保留 | 引导步骤、角色可见菜单筛选、跨页跳转和重新开始入口集中在一个 composable；首页没有复制第二套 tour。 |
| R12 | `src/api/home.ts:41-73`；`src/mocks/services/home.ts:82-137`；`src/pages/dashboard/index.vue:124-144` | `fetchMyTodos`、`fetchMyApprovals`、`fetchScoped*`、`fetchMyDashboard` | 保留 | 首页通过 `src/api` 聚合已有读接口；待办/审批按 `userId`、审批权限和 scope 裁剪，经营总览按允许店铺集合裁剪。首页 API 没有读取工资或工资条接口，页面没有直接访问 mock service。 |
| R13 | `src/pages/dashboard/index.vue:646-685` | Vuetify `VTable`、Vuexy dashboard table 形态 | 保留 | 这是经营总览卡片内的固定店铺摘要，不是可管理的业务列表；不需要分页、列设置或批量操作。金额仍调用统一 `formatMoney`。 |
| R14 | `src/views/gap-b/GapBPage.vue:319-342,468-487`；`src/components/biz/GapAPage.vue:607-628`；`src/views/gap-c/GapCPage.vue:966-989` | Vuetify `VTable`、Vuexy detail/editable table 形态 | 保留 | 合同价格、导入映射、报销行项目和有效权限结果分别是详情、向导或内嵌编辑区，使用固定列和行级控件，不能安全替换成带分页的通用列表。 |
| R15 | `src/pages/finance/imports/index.vue:2-14`；`src/components/biz/ScopedDataPreview.vue:2-11` | `src/api/*` 读接口；API 返回类型 | 保留 | 页面运行时请求分别走 `fetchImports`、scoped read API；对 `mocks/services` 的引用只有 `import type`，不会绕过 API 或直接调用 mock service。 |
| R16 | `src/pages/notifications.vue:1-3`；`src/pages/notifications/index.vue:1-24`；`src/pages/notifications/inbox.vue:1-67` | 消息收件箱单一数据源 | 保留 | 父路由只承载 `RouterView`，`/notifications` 复用 `InboxPage` 并传入同一 `fetchInboxNotifications`/`markInboxNotificationRead`，没有第二套消息列表或状态存储。 |
| R17 | `src/components/biz/AssistantDrawer.vue:84-95`；`src/config/pages.ts:2297-2305` | `findPageByPath` | 应替换（建议） | 助手重新实现了按路径排序、参数正则匹配和页面查找；项目已有 `findPageByPath`，两套实现将来可能对尾斜杠、参数页或通配页产生不同结果。建议直接复用配置层函数。 |
| R18 | `src/views/gap-b/GapBPage.vue:497-500` | `MoneyText` | 应替换（建议） | 导入向导预览把金额写成硬编码 `¥ 2,400.00`，与同页其它金额列的 `MoneyText` 不一致。即使当前是静态预览，也建议改为 `MoneyText`，避免示例单位或舍入规则漂移。 |
| R19 | `src/views/gap-c/GapCPage.vue:433-446` | `ListPage` 的 `actions` 插槽 | 应替换（建议） | SYS16 的「新增临时授权」放在 `#widgets` 中，动作位于统计/提示区而非统一页头。其它 U1 列表已经使用 `#actions`；建议迁移到标题行，减少跨批次布局差异。 |
| R20 | `src/plugins/1.router/index.ts:42-50`；`src/config/pages.ts:2279`；`src/pages/kb/index.vue:1-7`；`src/pages/kb/index/index.vue:1-7` | Vue Router 文件路由、K08 页面登记 | **必须修复** | `mapped` 已包含自动生成的 `/kb/index`，随后又无条件加入同路径的 `knowledgeIndex`。`pageCatalog` 还登记了 K08，两个文件路由分别对应首页/索引模式，当前依赖插入顺序掩盖重复记录，容易造成重复路由名和守卫/导航解析不一致。应保留一个规范 `/kb/index` 记录，并让 K08 的索引模式通过该唯一记录承载。 |

## 分项结论

### 1. 组件与 Vuexy 复用

批次 A–E 的通用列表、详情、表单、抽屉、状态、金额和权限 UI 已集中在 `components/biz`；Vuexy/Vuetify 只承担通用布局和业务专属内嵌表格。没有发现新的通用组件重复实现。聊天入口也已经共享 `ChatThread`，`ChatComposer`/`ChatMessage` 只是兼容适配层。

### 2. 跨批次重复实现

`actorId`、`MoneyText`、`StatusChip`、`PermissionGate` 和 `canRoleOpen` 的主路径已统一。发现的实际重复是助手中的 `matchPage`，应改为调用 `findPageByPath`。Gap B 的一处金额预览和 Gap C 的一处列表动作属于一致性建议。

### 3. 冲突痕迹、页面登记和 i18n

当前 diff 未发现重复导出、重复函数名或重复 i18n key。发现一处真实的 `/kb/index` 路由重复登记，列为「必须修复」；其余页面文件是按 `page-id` 传参的薄壳，没有重复业务 UI。

### 4. API 边界与数据范围

改动页面的运行时数据调用均从 `src/api` 导入。`mocks/services` 仅出现在类型导入或 API 实现内部；没有页面直接调用 mock service。首页聚合保持本人待办、合法审批、店铺 scope 和字段裁剪，`ScopedDataPreview` 与 `/me/data-scope` 复用同一 scoped read API。

### 5. UX U1–U3

U1 的列表页头和日历布局已复用 `ListPage` actions、`FinanceTablePage` actions 透传和 FullCalendar 响应式视图；U2 的 Shepherd tour 只由 `useOnboardingTour` 管理，首页由 `fetchHome` 聚合；U3 的两个入口均使用 `ChatThread`，历史按稳定 `session.userId` 和入口隔离，登出/换用户会使在途写入失效。

## 核验命令

| 命令 | 结果 |
| --- | --- |
| `pnpm exec tsx scripts/verify-u1.ts` | 通过：`[U1] static checks passed` |
| `pnpm exec tsx scripts/verify-u2.ts` | 未运行：当前工作树没有 `frontend/node_modules`，`pinia` 无法解析（`ERR_MODULE_NOT_FOUND`）。 |
| `pnpm exec tsx scripts/verify-u3.ts` | 未运行：当前工作树没有 `frontend/node_modules`，`pinia` 无法解析（`ERR_MODULE_NOT_FOUND`）。 |
| `pnpm exec tsx scripts/verify-home-access.ts` | 未运行：当前工作树没有 `frontend/node_modules`，`pinia` 无法解析（`ERR_MODULE_NOT_FOUND`）。 |

本审计没有启动 dev server，没有占用 `5173`/`4173` 端口，没有修改业务代码或测试文件。

## 必须修复清单

1. `src/plugins/1.router/index.ts:42-50` 与 `src/pages/kb/index.vue:1-7`、`src/pages/kb/index/index.vue:1-7` 共同造成 `/kb/index` 的重复路由记录。应保留单一规范注册，避免路由、守卫和导航解析依赖插入顺序。

其余两项为建议：复用 `findPageByPath`，并把 Gap B 预览金额改为 `MoneyText`；Gap C 的临时授权动作建议移到 `ListPage` 页头。
