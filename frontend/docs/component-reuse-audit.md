# 组件复用审计

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](./前端开发规范.md) 和 [对接真实接口](./对接真实接口.md)。


审计日期：2026-11-09  
审计范围：`src/components/**`、`src/views/**`，以及 `src/pages/dashboard`、`catalog`、`orders`、`inventory`、`procurement`、`logistics` 下的 Vue 页面。参考实现为 Vuexy full-version（只读）和 Vuetify 3.10。

本次审计以“先复用、后定制”为准。已有的业务组件继续保持薄封装；页面中的业务数据、路由、权限、i18n 和 `data-test` 属性没有迁移到展示组件中。

## 共享组件

| 自写组件/UI 块 | 位置 | 现成等价物（路径） | 处理（已替换/保留） | 原因 |
|---|---|---|---|---|
| 应用加载进度条 | `src/components/AppLoadingIndicator.vue` | Vuexy `src/components/AppLoadingIndicator.vue` | 保留（改编） | 与 Vuexy 文件一致，直接沿用模板实现，未重复造轮子。 |
| 搜索页头图 | `src/components/AppSearchHeader.vue` | Vuexy `src/components/AppSearchHeader.vue` | 保留（改编） | 与 Vuexy 搜索头组件一致，只保留项目需要的 props。 |
| 错误页头 | `src/components/ErrorHeader.vue` | Vuexy `src/components/ErrorHeader.vue` | 保留（改编） | 仅提供错误页标题/描述，结构沿用 Vuexy。 |
| 价格卡片 | `src/components/AppPricing.vue` | Vuexy `src/components/AppPricing.vue` | 保留（改编） | 仅用于模板演示页，使用 Vuexy 卡片和图片资源。 |
| `AddAuthenticatorAppDialog` | `src/components/dialogs/AddAuthenticatorAppDialog.vue` | Vuexy `src/components/dialogs/AddAuthenticatorAppDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 文件与 Vuexy 对应实现一致，仅由本项目认证页按需调用。 |
| `AddEditAddressDialog` | `src/components/dialogs/AddEditAddressDialog.vue` | Vuexy `src/components/dialogs/AddEditAddressDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板地址表单，不新增项目级通用表单外壳。 |
| `AddEditPermissionDialog` | `src/components/dialogs/AddEditPermissionDialog.vue` | Vuexy `src/components/dialogs/AddEditPermissionDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板权限编辑弹窗。 |
| `AddEditRoleDialog` | `src/components/dialogs/AddEditRoleDialog.vue` | Vuexy `src/components/dialogs/AddEditRoleDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板角色权限表单。 |
| `AddPaymentMethodDialog` | `src/components/dialogs/AddPaymentMethodDialog.vue` | Vuexy `src/components/dialogs/AddPaymentMethodDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板支付方式弹窗和卡片资源。 |
| `CardAddEditDialog` | `src/components/dialogs/CardAddEditDialog.vue` | Vuexy `src/components/dialogs/CardAddEditDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板银行卡表单。 |
| `ConfirmDialog` | `src/components/dialogs/ConfirmDialog.vue` | Vuexy `src/components/dialogs/ConfirmDialog.vue` | 保留（已复用） | 确认/取消交互直接沿用 Vuexy，业务文案由调用方传入。 |
| `CreateAppDialog` | `src/components/dialogs/CreateAppDialog.vue` | Vuexy `src/components/dialogs/CreateAppDialog.vue`、`AppStepper.vue` | 保留（Vuexy 改编） | 复用模板分步弹窗和步骤组件。 |
| `EnableOneTimePasswordDialog` | `src/components/dialogs/EnableOneTimePasswordDialog.vue` | Vuexy `src/components/dialogs/EnableOneTimePasswordDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板一次性密码弹窗。 |
| `PaymentProvidersDialog` | `src/components/dialogs/PaymentProvidersDialog.vue` | Vuexy `src/components/dialogs/PaymentProvidersDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板支付提供商展示。 |
| `PricingPlanDialog` | `src/components/dialogs/PricingPlanDialog.vue` | Vuexy `src/components/dialogs/PricingPlanDialog.vue` | 保留（Vuexy 改编） | 复用模板价格方案弹窗。 |
| `ReferAndEarnDialog` | `src/components/dialogs/ReferAndEarnDialog.vue` | Vuexy `src/components/dialogs/ReferAndEarnDialog.vue`、`AppStepper.vue` | 保留（Vuexy 改编） | 复用模板邀请步骤和弹窗结构。 |
| `ShareProjectDialog` | `src/components/dialogs/ShareProjectDialog.vue` | Vuexy `src/components/dialogs/ShareProjectDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板成员分享弹窗。 |
| `TwoFactorAuthDialog` | `src/components/dialogs/TwoFactorAuthDialog.vue` | Vuexy `src/components/dialogs/TwoFactorAuthDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板二次验证选择弹窗。 |
| `UserInfoEditDialog` | `src/components/dialogs/UserInfoEditDialog.vue` | Vuexy `src/components/dialogs/UserInfoEditDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板用户资料编辑弹窗。 |
| `UserUpgradePlanDialog` | `src/components/dialogs/UserUpgradePlanDialog.vue` | Vuexy `src/components/dialogs/UserUpgradePlanDialog.vue`、Vuetify `VDialog` | 保留（Vuexy 改编） | 复用模板升级方案弹窗。 |
| KPI 统计卡 | `src/components/KpiCard.vue` | Vuexy `src/@core/components/cards/CardStatisticsHorizontal.vue` | 保留（薄封装） | 直接渲染 `CardStatisticsHorizontal`，只补 CrossERP 需要的 hint；没有重复实现卡片。 |
| 占位页 | `src/components/PlaceholderPage.vue` | Vuetify `VCard`、`VChip` | 保留（薄封装） | 需要展示 CrossERP 页面目录、阶段和路由元数据，Vuetify 只提供外壳。 |
| 助手抽屉 | `src/components/biz/AssistantDrawer.vue` | Vuetify `VNavigationDrawer`；Vuexy `src/pages/apps/chat.vue` | 保留（改编） | 复用了聊天气泡、输入条和抽屉外壳；业务只读适配器与建议提交属于 CrossERP。 |
| 确认弹窗宿主 | `src/components/biz/ConfirmHost.vue` | Vuexy `src/components/dialogs/ConfirmDialog.vue` | 保留（已复用） | `useConfirm()` 只负责 Promise 状态，实际弹窗直接使用 Vuexy `ConfirmDialog`。 |
| 列表页地基 | `src/components/biz/ListPage.vue` | Vuexy product/user/invoice list；`VDataTableServer`；`TablePagination.vue` | 保留（薄封装） | 统一筛选、列设置、保存视图、导出和批量操作，页面仍传入数据和插槽。 |
| 详情页地基 | `src/components/biz/DetailPage.vue` | Vuexy invoice/order detail；`VTimeline` | 保留（薄封装） | 复用详情左右栏和时间线，只增加 CrossERP 状态、关联单据和审计轨迹。 |
| 表单抽屉 | `src/components/biz/FormDrawer.vue` | Vuexy `src/views/apps/user/list/AddNewUserDrawer.vue`、`AppDrawerHeaderSection.vue` | 保留（已改编） | 抽屉、滚动和 `VForm` 骨架直接来自 Vuexy，保存事件交给页面 API。 |
| 整页表单 | `src/components/biz/FormPage.vue` | Vuexy `src/views/apps/invoice/InvoiceProductEdit.vue`、Vuetify `VForm`/`VRow`/`VCol` | 保留（已改编） | 沿用 Vuexy 商品/发票编辑页的顶栏操作与表单校验结构；参考目录没有同名 product add 页面。 |
| 只读记录抽屉 | `src/components/biz/RecordDrawer.vue` | Vuexy `AddNewUserDrawer.vue` 外壳；`AppDrawerHeaderSection.vue`；`PerfectScrollbar` | 保留（薄封装） | 只读内容没有 Vuexy 业务等价物，抽屉壳已直接复用。 |
| 空状态 | `src/components/biz/EmptyState.vue` | Vuetify `VEmptyState` | 保留（薄封装） | 仅统一 i18n 文案和图标。 |
| 加载状态 | `src/components/biz/LoadingState.vue` | Vuetify `VSkeletonLoader` | 保留（薄封装） | 仅统一 skeleton 类型和无障碍文案。 |
| 错误状态 | `src/components/biz/ErrorState.vue` | Vuetify `VAlert` | 保留（薄封装） | 统一错误标题、重试事件和 i18n；不重复定义错误卡片样式。 |
| 状态标签 | `src/components/biz/StatusChip.vue` | Vuetify `VChip`；Vuexy `pages/components/chip.vue` | 保留（确无等价物） | `domain + value` 状态字典、中英文名称和颜色是 CrossERP 业务规则，`VChip` 本身不具备。 |
| 金额文本 | `src/components/biz/MoneyText.vue` | Vuetify `VText`/`VChip` 无金额组件 | 保留（确无等价物） | 需要币种和调用方传入的折算金额展示；组件只格式化，不计算汇率。 |
| 权限门 | `src/components/biz/PermissionGate.vue` | Vuexy CASL 插件 | 保留（确无等价物） | Vuexy CASL 的权限模型不是 CrossERP 五种角色，必须继续调用项目 `can(role, action)`。 |
| 聊天气泡 | `src/views/apps/chat/ChatLog.vue` | Vuexy `src/views/apps/chat/ChatLog.vue` | 保留（已改编） | 去掉演示 store，保留 Vuexy 的消息分组和气泡布局供两个入口复用。 |
| 聊天输入条 | `src/views/apps/chat/ChatMessageForm.vue` | Vuexy `src/pages/apps/chat.vue` 的 message input | 保留（已改编） | 复用输入条结构，保留项目发送、加载和 i18n 接口。 |
| 库存分类列表 | `src/views/inventory/KindStock.vue` | Vuexy logistics dashboard 列表形态、`ListPage` | 保留（薄封装） | 业务分类和库存字段是项目特有，列表交给共享 `ListPage`。 |
| 登录社交按钮 | `src/views/pages/authentication/AuthProvider.vue` | Vuexy authentication provider block | 保留（改编） | 仅替换主题颜色，使用 Vuexy 的图标按钮结构。 |

## 页面中的 UI 块

| 自写组件/UI 块 | 位置 | 现成等价物（路径） | 处理（已替换/保留） | 原因 |
|---|---|---|---|---|
| 统计卡 | `src/pages/dashboard/index.vue`、`src/pages/finance/recon.vue`、`src/pages/inventory/on-hand.vue`、`src/pages/orders/channels.vue`、`src/pages/orders/[id].vue` | Vuexy `CardStatisticsHorizontal.vue` | 已替换 | 页面统一通过 `KpiCard` 渲染 Vuexy 统计卡，保留 hint、权限和数据字段。 |
| 仪表盘趋势/分布图 | `src/pages/dashboard/index.vue` | Vuexy dashboards/ecommerce 图表；项目 Apex/Chart.js 配置 | 保留（改编） | 图表数据和指标是 CrossERP 特有，图表容器及库组件已复用。 |
| 仪表盘店铺排名表 | `src/pages/dashboard/index.vue` | Vuetify `VTable`；Vuexy dashboard table | 保留（直接使用） | 这是卡片内的固定排名摘要，不需要分页、列设置或导出；直接使用 Vuetify 表格。 |
| 仪表盘快捷入口和预算卡 | `src/pages/dashboard/index.vue`、`src/pages/dashboard/todos.vue`、`src/pages/dashboard/stores.vue` | Vuetify `VCard`/`VList`；Vuexy dashboard card examples | 保留（直接使用） | 这些是固定摘要和路由入口，直接使用 Vuetify/Vuexy 卡片外壳，不另建卡片组件。 |
| 日历筛选侧栏和日历 | `src/pages/dashboard/calendar.vue` | Vuexy `src/pages/apps/calendar.vue`、`src/views/apps/calendar/CalendarEventHandler.vue`、FullCalendar | 保留（已改编） | 使用同样的 `VNavigationDrawer`、`AppDateTimePicker` 和 FullCalendar；项目不创建事件，因此不引入 Vuexy 的事件编辑器。 |
| 采购新建步骤条 | `src/pages/procurement/orders/new.vue` | Vuexy `src/@core/components/AppStepper.vue`、`src/pages/wizard-examples/create-deal.vue` | 已替换 | 步骤导航使用共享 `AppStepper`，步骤数据和表单字段仍由页面维护。 |
| 订单/采购/物流详情页标签与时间线 | `src/pages/orders/[id].vue`、`src/pages/procurement/orders/[id].vue`、`src/pages/procurement/suppliers/[id].vue`、`src/pages/logistics/shipments/[id].vue` | Vuexy invoice/order detail、user view 的 `VTabs`/`VWindow`、`VTimeline` | 保留（已改编） | 页面使用 `DetailPage` 和 Vuetify/Vuexy 标签、窗口、时间线；只保留业务字段和流转按钮。 |
| 目录 SKU/Listing 详情 | `src/pages/catalog/skus/[id].vue`、`src/pages/catalog/listings/[id].vue` | Vuexy order details + `DetailPage`、`FormDrawer` | 保留（已改编） | 详情外壳和成本编辑抽屉走共享组件，状态、成本和关联单据为业务内容。 |
| 列表筛选、分页、批量工具栏 | `src/pages/catalog/**`、`src/pages/orders/**`、`src/pages/inventory/**`、`src/pages/procurement/**`、`src/pages/logistics/**` | `ListPage`（内部为 `VDataTableServer`、`TablePagination`、App form elements） | 已替换 | 目标目录内的列表页统一使用 `ListPage`，没有页面级重复实现筛选和分页。 |
| 新建/编辑表单抽屉 | `src/pages/catalog/**`、`src/pages/inventory/**`、`src/pages/logistics/**`、`src/pages/procurement/suppliers/**` | `FormDrawer`（Vuexy `AddNewUserDrawer` 外壳） | 已替换 | 页面只保留字段、校验和 API 调用；抽屉、滚动、关闭和保存按钮由共享组件提供。 |
| 采购/库存明细表格 | `src/pages/procurement/orders/[id].vue`、`src/pages/inventory/inbound.vue`、`outbound.vue`、`transfers.vue`、`counts.vue` | Vuetify `VTable`；Vuexy invoice editable table | 保留（直接使用） | 这些表格含行级业务编辑和盘盈盘亏差异，不能套用分页列表；使用 Vuetify 表格并保持原有 `data-test`。 |
| 文件上传控件 | `src/pages/catalog/costs.vue` | Vuetify `VFileInput`；Vuexy `src/pages/forms/file-input.vue` | 保留（直接使用） | 单文件选择无需自写上传组件，已使用 Vuetify 控件和原型既有 API。 |
| 详情错误提示块 | `src/pages/catalog/skus/[id].vue`、`src/pages/catalog/listings/[id].vue`、`src/pages/orders/[id].vue`、`src/pages/procurement/suppliers/[id].vue`、`src/pages/procurement/orders/[id].vue`、`src/pages/logistics/shipments/[id].vue` | 共享 `ErrorState`（内部为 `VAlert`） | 已替换 | 详情加载/操作失败统一使用可重试错误状态，保留原错误文案和 `load` 流程。 |
| 其他页面状态提示 | `src/pages/**` 其余页面 | `ErrorState`、`LoadingState`、`EmptyState`、Vuetify `VAlert` | 保留（按语义） | 加载、空数据、表单保存失败和业务警告语义不同；已复用共享状态组件，必要时直接使用 Vuetify 警告。 |

## 审计结论

- 已确认的通用交互均落在 Vuexy/Vuetify 或 CrossERP 薄封装上：列表使用 `ListPage`，详情使用 `DetailPage`，抽屉使用 `FormDrawer`/`RecordDrawer`，统计使用 `KpiCard`，步骤条使用 `AppStepper`。
- 保留的组件只承载状态字典、金额格式化、五角色权限、只读智能助手和业务字段等 CrossERP 特有职责，没有复制一套通用 UI。
- 本次实际替换：六个目录/订单/采购/物流详情页的错误提示改为共享 `ErrorState`；其余页面中已存在的 Vuexy/Vuetify 复用按上表核对，未改变路由、数据中心、流转、权限、i18n 或 `data-test`。

## 补齐批次 0 复用审计

审计范围：相对 `a6f81ae` 的所有未提交 `frontend/` 新增/修改文件（24 个）。Vuexy 参考目录为 `D:/make/write/vue/vuexy-10.11.1/vuexy-admin-v10.11.1/vue-version/typescript-version/full-version`；同时核对 Vuetify 3 组件。批次 0 只补权限、类型、适配器和占位页元数据，未新增业务页面。

| 自写组件/UI 块 | 位置 | 现成等价物（路径） | 处理（已替换/保留） | 原因 |
| --- | --- | --- | --- | --- |
| 助手抽屉及滚动到底部行为 | `src/components/biz/AssistantDrawer.vue` | Vuexy `src/pages/apps/chat.vue`、`src/views/apps/chat/ChatLog.vue`；Vuetify `VNavigationDrawer`；`vue3-perfect-scrollbar` | 保留（改编） | 抽屉、聊天消息和输入条已经复用 Vuexy；滚动监听只服务 CrossERP 的只读智能体卡片，不重复实现聊天 UI。 |
| 权限门 | `src/components/biz/PermissionGate.vue` | Vuexy `src/@layouts/plugins/casl.ts` | 保留（业务薄封装） | Vuexy CASL 只提供通用能力，CrossERP 还要合并五角色、临时授权和 AI 收窄权限；模板仅保留 slot 显示控制。 |
| 角色切换器 | `src/layouts/components/RoleSwitcher.vue` | Vuetify `VBtn`、`VMenu`、`VList`；Vuexy vertical layout role/menu pattern | 保留（直接复用） | 结构全由 Vuetify 提供，只将角色目录名称接入 `roleTemplates`，没有新增菜单组件。 |
| 校验错误文案适配 | `src/@core/utils/validators.ts` | Vuexy `@core/utils/validators.ts`；Vue I18n | 保留（改编） | 校验规则沿用 Vuexy，新增 `configureValidatorI18n` 仅替换文案来源，避免页面各自手写错误提示。 |
| 智能体卡片适配器 | `src/agent/adapter.ts` | Vuexy `src/views/apps/chat/ChatLog.vue`（消息渲染） | 保留（确无等价物） | `AgentCard` 的证据、置信度、自主等级和建议 ID 是 CrossERP 只读业务协议，Vuexy 没有对应数据模型；文件不渲染 UI。 |
| 权限计算、自治等级和职责分离纯函数 | `src/utils/permission-engine.ts`、`src/utils/autonomy.ts`、`src/utils/duties.ts` | Vuexy CASL 插件；Vuetify 无业务等价物 | 保留（确无等价物） | 角色继承、临时授权、金额动作硬上限和审批职责分离是业务规则，不能用展示组件替代；均为纯逻辑，无自写 UI。 |
| 批次 0 占位页元数据 | `src/config/pages.ts` | `src/components/PlaceholderPage.vue`；Vuetify `VCard`、`VChip` | 保留（直接复用） | 仅修正 98 个占位页的英文名、图标和权限 key；渲染仍走既有 `PlaceholderPage`，路由、`to: { path }`、角色、i18n 和 `data-test` 不变。 |
| 权限目录扩展 | `src/config/permissions.ts`、`src/types/foundation.ts`、`src/stores/permissions.ts`、`src/api/foundation.ts`、`src/mocks/services/foundation*.ts` | Vuexy CASL 类型/插件 | 保留（确无等价物） | 这些是权限点、审批快照和只读 API 的数据契约，不包含页面结构；新增 DocType key 与 ERPNext/Odoo 命名对齐。 |

处理结果：本批次发现的 UI 块均已使用 Vuexy/Vuetify 或现有 CrossERP 薄封装，没有需要再复制替换的通用结构；保留项均有上述业务差异理由。

---

# 第 2 批（财务/审批/广告）组件复用审计

## 第 2 批组件复用检查

审计范围：`frontend/src/pages/finance/**`、`frontend/src/pages/ads/**`、`frontend/src/pages/approvals/**`、`frontend/src/views/finance/**`，以及相对 `05c91d2` 的 `frontend/src/components` 变更。对照 Vuexy full-version（`D:/make/write/vue/vuexy-10.11.1/vuexy-admin-v10.11.1/vue-version/typescript-version/full-version`）和 Vuetify 组件。

本批次相对基线没有新增 `src/components` 组件；`components/biz/EmptyState.vue`、`components/biz/MoneyText.vue` 是已有共享组件的修改，不重复造组件。

| 组件/页面块 | 位置 | 对应 Vuexy/Vuetify 组件 | 处理（已替换/保留） | 理由 |
| --- | --- | --- | --- | --- |
| 通用财务列表表格、筛选、分页 | `views/finance/FinanceTablePage.vue` | 项目 `ListPage`；底层 `VDataTableServer` | 保留 | 已经通过共享列表封装复用 Vuexy 列表模式，页面只提供列和数据。 |
| 财务列表 KPI 区 | `views/finance/FinanceTablePage.vue` | 项目 `KpiCard`；Vuexy `CardStatisticsHorizontal` | 保留 | `KpiCard` 是现有薄封装，统一了统计卡片和提示文本。 |
| 财务详情页双栏、时间线、关联项 | `views/finance/FinanceDetail.vue` | 项目 `DetailPage`；Vuexy ecommerce detail / `VTimeline` | 保留 | 已集中复用详情壳和时间线，避免各详情页重复布局。 |
| 文件导入选择卡片 | `views/finance/FinanceUpload.vue` | Vuetify `VCard`、`VFileInput`、`VAlert`、`VBtn`；Vuexy `@core/components/DropZone.vue` | 保留 | Vuexy `DropZone` 当前实现限定图片类型并带图片预览，不适用于 CSV/TXT/XLSX；`VFileInput` 是该场景的直接 Vuetify 等价物。 |
| 审批待办列表 | `pages/approvals/index.vue` | 项目 `ListPage`、`MoneyText`、`StatusChip` | 保留 | 已使用共享列表、金额和状态组件。 |
| 审批待办 KPI | `pages/approvals/index.vue` | 项目 `KpiCard`；Vuexy `CardStatisticsHorizontal` | 保留 | 使用现有 KPI 封装，没有新增卡片实现。 |
| 审批决定抽屉 | `pages/approvals/index.vue` | Vuetify `VNavigationDrawer`、`VCard`、`VTable`；Vuexy drawer 模式 | 保留 | 这是只读快照加“批准/驳回”双动作；项目 `FormDrawer` 强制表单校验和单一保存动作，不适配该交互。 |
| 审批详情快照表 | `pages/approvals/[id].vue` | Vuetify `VCard`、`VTable`、项目 `MoneyText` | 保留 | 使用 Vuetify 标准表格和共享金额组件，表格字段与审批快照强绑定。 |
| 审批意见表单 | `pages/approvals/[id].vue` | `AppTextarea`、`VAlert`、`VBtn` | 保留 | Vuexy/Vuetify 已提供基础控件，没有同语义的现成业务组件。 |
| 已提交审批列表 | `pages/approvals/submitted.vue` | 项目 `FinanceTablePage`、`StatusChip`、`MoneyText` | 保留 | 已复用财务列表和共享单元格渲染。 |
| 审批流程步骤说明 | `pages/approvals/workflows.vue` | Vuetify `VExpansionPanels`；Vuexy expansion panel 示例 | 保留 | 现有 Vuetify 展开面板就是对应实现；页面没有自绘步骤器。 |
| 广告活动列表 | `pages/ads/campaigns.vue` | 项目 `FinanceTablePage` / `ListPage` | 保留 | 直接复用共享列表。 |
| 广告导入上传与列表 | `pages/ads/imports.vue` | 项目 `FinanceUpload`、`FinanceTablePage`、`MoneyText` | 保留 | 上传和列表均由现有共享组件提供。 |
| 广告效果图表 | `pages/ads/performance.vue` | Vuexy 已集成的 `VueApexCharts` / ApexCharts | 保留 | 使用项目已有图表插件和主题 composable，没有另写 SVG 或 canvas。 |
| 广告费分摊表单 | `pages/ads/allocations.vue` | Vuetify `VCard`、`VRow/VCol`、`AppTextField`、`VAlert`、`VBtn` | 保留 | 这是页面内的两字段快速编辑；抽屉会增加操作路径，现有 Vuetify 表单控件已满足需求。 |
| 利润按店铺图表 | `pages/finance/profit/index.vue` | Vuexy 已集成的 `VueApexCharts` | 保留 | 复用现有图表组件和主题配置。 |
| 利润按店铺表金额列 | `pages/finance/profit/index.vue` | 项目 `MoneyText` | 已替换 | 将 6 个重复的 `formatMoney` 模板统一到共享金额组件，保持万分位转换和币种格式一致。 |
| 利润按 SKU 表金额列 | `pages/finance/profit/index.vue` | 项目 `MoneyText` | 已替换 | 将 6 个重复的 `formatMoney` 插槽统一到共享金额组件。 |
| SKU 利润 KPI 网格 | `pages/finance/profit/sku/[internalSku].vue` | 项目 `KpiCard`；Vuexy `CardStatisticsHorizontal` | 保留 | 统计卡片已使用共享 KPI 封装；该组件的 stats 接口是纯文本，不另造卡片。 |
| 汇率新增抽屉 | `pages/finance/fx-rates.vue` | 项目 `FormDrawer`、`AppSelect`、`AppTextField` | 保留 | 已使用项目对 Vuexy 用户新增抽屉模式的封装。 |
| 收付款核销候选布局 | `pages/finance/clearing.vue` | Vuetify `VTable`、`VList`、`VCheckbox`、项目 `MoneyText`/`StatusChip` | 保留 | 左侧可多选表格和右侧候选清单是特定业务的双栏布局，没有可直接替换的单一共享组件。 |
| 凭证列表 | `pages/finance/vouchers/index.vue` | 项目 `ListPage`、`KpiCard`、`MoneyText`、`StatusChip` | 保留 | 已完整复用共享列表、KPI、金额和状态组件。 |
| 凭证详情分录表 | `pages/finance/vouchers/[id].vue` | 项目 `DetailPage`、`MoneyText`；Vuetify `VTable` | 保留 | 详情壳、金额和表格均使用现有组件，分录列是业务专属。 |
| 异常列表 | `pages/finance/issues/index.vue` | 项目 `ListPage`、`KpiCard`、`MoneyText`、`StatusChip` | 保留 | 已复用共享列表及单元格组件。 |
| 异常详情处理卡片 | `pages/finance/issues/[id].vue` | 项目 `DetailPage`、`MoneyText`；`AppTextarea`/`VAlert` | 保留 | 共享详情壳和金额组件已覆盖通用结构，处理动作和提示是业务专属。 |
| 对账列表 | `pages/finance/recon/index.vue` | 项目 `ListPage` / `KpiCard` | 保留 | 已使用共享列表和 KPI，服务层提供的数据形状保持不变。 |
| 结算列表 | `pages/finance/settlements/index.vue` | 项目 `FinanceTablePage` / `ListPage` | 保留 | 已使用共享列表，服务层提供的数据形状保持不变。 |
| 结算详情总额 | `pages/finance/settlements/[id].vue` | 项目 `MoneyText` | 已替换 | 将手写的“显示值 + 币种”统一为共享金额组件，避免重复格式化。 |
| 结算详情明细金额 | `pages/finance/settlements/[id].vue` | 项目 `MoneyText` | 已替换 | 明细金额统一走共享组件，保留负数和币种格式。 |
| 导入批次、原始行详情 | `pages/finance/imports/[id].vue`、`pages/finance/rows/[table]/[id].vue` | 项目 `FinanceDetail`、`EmptyState`；Vuetify `VCard/VTable` | 保留 | 已复用详情页和空状态，字段/JSON 原文属于审计数据专用展示。 |
| 对账运行详情 | `pages/finance/recon/[id].vue` | 项目 `FinanceDetail`、`KpiCard`；Vuetify `VTable/VChip` | 保留 | 已复用详情壳和 KPI；匹配组原因码表格无通用业务包装。 |
| 应收、应付、资金、科目、列映射、费用映射、导出列表 | `pages/finance/ar.vue`、`ap.vue`、`cash.vue`、`accounts.vue`、`column-maps.vue`、`fee-map.vue`、`exports.vue` | 项目 `FinanceTablePage`；Vuetify `VChip`/`VBtn` | 保留 | 页面均是共享列表加少量状态或操作插槽，没有重复自定义表格。 |

### 汇总

- 审计条目：32 个（按可独立替换的页面块计数；同一共享列表在多个页面按页面族合并记录）。
- 已替换：4 个页面块，涉及 2 个文件：利润页店铺表金额列、SKU 表金额列、结算详情总额、结算详情明细金额。
- 保留：28 个页面块。保留原因集中为：已经使用项目共享封装；Vuetify 原生组件就是 Vuexy 对应实现；或业务交互（文件类型、双动作审批抽屉、核销双栏）没有安全的一对一替代。
- 共享文件编辑：无。组件替换只修改了范围内的两个页面文件并新增本审计文档；列表路由文件名调整由独立的批次路由修复提交完成。

### 复查（第 2 批最后一轮）

复查基线：`a661287`；范围为 `git diff --stat a661287 HEAD -- frontend/src` 列出的变更文件，重点检查 `frontend/src/pages/ads/**`、`frontend/src/pages/approvals/**`、`frontend/src/pages/finance/**`、`frontend/src/views/finance/**`，并核对现有 `src/components` 与 `src/@core` 组件。

检查文件：广告活动/导入/效果/分摊页面，审批列表/详情/流程页面，财务科目、应收、应付、资金、核销、列映射、利润、结算、凭证页面，以及 `views/finance/FinanceTablePage.vue`；API、mock、i18n、类型文件只作为页面数据形状的辅助核对。

- 新增组件：0 个；变更集中在既有页面和 `FinanceTablePage`，没有新增 `.vue` 组件文件。
- 复用结论：列表、筛选、分页继续使用 `FinanceTablePage`/`ListPage`；统计使用 `KpiCard`；详情使用 `FinanceDetail`/`DetailPage`；状态和金额使用 `StatusChip`/`MoneyText`；流程编辑使用 `AppStepper`、`FormDrawer`、`AppSelect`、`AppTextField`。页面中的 Vuetify 卡片、表格、双栏核销和审批双动作抽屉均为业务专属布局，保留合理。
- 发现：`pages/finance/profit/sku/[internalSku].vue` 的六个 SKU 利润 KPI 仍以字符串直接拼接金额和币种；`pages/finance/recon/[id].vue` 的匹配组金额仍直接插值。两处需要改造 `KpiCard` 或表格插槽才能完整接入 `MoneyText`，本轮未扩大共享组件范围，记录为后续事项。
- 已替换：`pages/finance/vouchers/[id].vue` 的未平衡差额改用已有 `MoneyText`，避免在状态芯片中直接渲染原始金额。
- 其他金额列已保持或采用 `MoneyText`（广告、应收/应付、资金、审批、利润表、结算、凭证分录、异常详情）；未发现可安全一对一替换的重复页面壳。

---

# 第 3 批（CRM/智能体中心/审计/设置）组件复用审计

### 第3批（CRM/智能体/审计/设置）

第 3 批页面优先复用 Vuexy 与 Vuetify：列表统一使用 `ListPage`，详情统一使用 `DetailPage`、`VTabs`/`VWindow` 与 `VTimeline`，表单使用 `FormPage`/`FormDrawer`。智能体路由组件已移到 `src/views/agent/`，审计组件已移到 `src/views/audit/`，CRM 看板改编 Vuexy Kanban 的 FormKit 拖拽实现并放在 `src/views/crm/kanban/`。原 `ModuleTable`、`StageBoard` 和页面目录下的大型 workspace 组件已删除，页面仍只调用 `src/api/*`。完整逐页来源与处理记录见 本文「第 3 批补充记录」一节。

## 第 3 批补充记录（原 batch3-component-audit.md）

### 第 3 批组件复用审计

#### 自写组件/区块与现有等价实现

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

#### 页面与 Vuexy 来源

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

#### 路由检查

`src/config/pages.ts` 中 `/crm`、`/agent`、`/audit`、`/security-log`、`/admin`、`/account` 前缀的已实现页面均有对应 `.vue` 文件；本配置没有 `/llm` 路由。页面目录未再放置业务组件，因此 Vite 文件路由不会把审计或智能体组件误识别为路由。

所有页面继续通过 `src/api/*` 读取或提交 mock 数据；智能体写操作只调用审批服务，金额仍由服务层提供。

## 合并后整体复用审计

### 检查范围

检查 `frontend/src/pages`、`frontend/src/views`、`frontend/src/components`（含三批合并后的业务页面、Vuexy 改编组件和 `components/biz` 共享地基），并对照 Vuexy 10.11.1 源码与 Vuetify 组件，重点核对列表、详情、加载状态、抽屉、上传、步骤条、时间线、状态标签、空状态、金额显示和统计卡。

### 本轮替换

| 文件 | 原实现 | 改用的组件 |
|---|---|---|
| `src/views/agent/AgentListPage.vue` | 页面内直接写 `VSkeletonLoader` 加载骨架 | `components/biz/LoadingState.vue` |
| `src/views/agent/AgentDetailPage.vue` | 页面内直接写 `VSkeletonLoader` 加载骨架 | `components/biz/LoadingState.vue` |

这两处只统一加载状态的 UI 外壳，未改变加载条件、API 调用、路由、数据或业务逻辑。

### 保留的自定义组件与原因

- `components/biz/ListPage.vue`、`DetailPage.vue`、`FormDrawer.vue`、`KpiCard.vue`：均为已有 Vuexy/Vuetify 组件的薄封装，承载跨页面筛选、分页、详情时间线、表单校验和提示文案；财务、库存、审计、智能体页面已经复用它们。
- `components/biz/StatusChip.vue`、`MoneyText.vue`、`PermissionGate.vue`：分别包含 CrossERP 状态字典、金额/币种展示和角色权限语义，Vuexy/Vuetify 没有同语义组件。
- `views/finance/FinanceUpload.vue`：使用 Vuetify `VFileInput` 处理 CSV/TXT/XLSX；Vuexy `DropZone` 面向图片预览，不能直接替换。
- `pages/approvals/index.vue` 的审批决定抽屉：包含只读快照及批准/驳回双动作，`FormDrawer` 的单一保存表单语义不匹配。
- `pages/dashboard/calendar.vue` 的日历筛选抽屉和 FullCalendar：复用 Vuexy 日历模式及 Vuetify 外壳，属于日历专用交互。
- 业务详情中的分录、核销、库存盘点和工具权限矩阵表格：字段、行级动作或多选语义专属，直接使用 Vuetify `VTable` 比套通用列表更安全。




## 补齐批次 0

批次 0 没有新增业务页面组件，98 条新路由统一复用现有 `components/PlaceholderPage.vue`。权限、AI 状态、渠道和校验属于共享地基，分别复用 Pinia、现有 `PermissionGate`、`AssistantDrawer`、`ChatLog` 与 `vue-i18n`；没有重复实现 Vuexy 页面或聊天卡片。


## 补齐批次 A


| 页面/组件 | 复用内容 | 新增原因 |
|---|---|---|
| `components/biz/GapAPage.vue` | `ListPage`、`DetailPage`、`KpiCard`、`MoneyText`、`StatusChip`、`AssistantDrawer` | 批次 A 的费用、总账、报表和结账共用一套确定性 mock 状态；现有单一领域页面无法表达这些跨页流程，因此新增批次专用编排壳。 |
| `pages/expense/claims/new.vue` | `AppTextField`、`AppTextarea`、`VForm` | 复用现有表单控件；AI 预填只显示 `VAlert`/`VChip`，没有新增 AI 对话界面。 |
| `pages/finance/vouchers/[id].vue` | `DetailPage`、`MoneyText`、`VTimeline` | 凭证来源追溯需要把结算单、订单和审计时间轴放在同一详情页，现有凭证详情字段不足。 |

订单到凭证、报销审批和利润凭证都通过 `src/api/gap-a.ts` 调用批次专用 mock；金额展示统一使用 `MoneyText`，金额生成和审批护栏在服务层完成。

## 补齐批次 A 独立复用审计

本节按 `docs/design/01-前端页面设计.md` 的 EX01–EX07、F23–F34 逐页核对。页面路由文件只保留 `GapAPage` 的薄包装；跨页面的列表筛选、分页、列管理、导出和空/错/加载态由 `ListPage` 提供，详情双栏、时间线和关联记录由 `DetailPage` 提供，金额由 `MoneyText` 提供，业务状态由 `StatusChip` 提供。

| 组件/UI 块 | 位置 | 现成等价物 | 处理 | 原因 | 业务操作是否满足 |
|---|---|---|---|---|---|
| 批次 A 通用编排壳 | `src/components/biz/GapAPage.vue` | 项目 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`MoneyText`、`StatusChip`、`PermissionGate`；Vuexy `apps/invoice/*` | 保留为薄组合；移除重复表单壳和手写状态 Chip | 19 页共享加载/错误/权限/金额规则，差异仅是字段与动作 | 已覆盖列表、详情、人工审批、AI 开关与审计时间线 |
| 页面路由包装 | `src/pages/expense/{claims,loans,trips,policies}/*`、`src/pages/finance/{cogs,fx-revaluation,gl,period-close,trial-balance,statements,tax,budgets}/*` | Vuexy 页面路由只负责装配业务视图 | 保留 7 行左右薄包装 | 避免每个页面重复 API、状态和表格模板 | 路由、权限点和 `data-test` 不变 |
| 报销新建表单 | `GapAPage.vue` 的 EX02 | `FormPage`；Vuexy `apps/invoice/add/index.vue`；`DropZone`/`AppDateTimePicker` 为可替换控件 | 改用 `FormPage` 顶栏保存/取消、右栏提交检查，保留 AI 预填和人工填写 | 原实现手写 `VCard`/`VForm`，重复了统一表单布局 | AI 开启可预填；AI 关闭仍可人工提交；超标准由服务层拦截 |
| 报销审批详情 | EX03 分支 | `DetailPage`、`MoneyText`、`PermissionGate`；Vuexy `apps/invoice/preview/[id].vue` | 保留字段专属 `VTable`，审批按钮改由 `PermissionGate` 包裹；时间线优先读 `fetchGapAAudits` | 明细行和审批动作不是通用列表字段，时间线必须保留审计来源 | 提交、主管批、财务批、驳回、凭证关联和审计记录均可用 |
| 借款列表/还款 | EX04 分支 | `ListPage`、`FormDrawer`；Vuexy `InvoiceAddPaymentDrawer` | 增加状态筛选、`登记还款` `FormDrawer`，余额更新仍走服务层 | 原页面只有展示，缺少设计要求的还款登记 | 列表、详情、还款和报销冲抵均可用 |
| 借款详情 | EX05 分支 | `DetailPage`、Vuexy invoice preview/timeline | 保留三张 KPI 卡和专属冲抵按钮；时间线接审计接口 | 借款余额与冲抵是领域字段，套通用表格会丢失语义 | 查看借/还/冲抵记录；冲抵动作可用 |
| 差旅列表/新建 | EX06 分支 | `ListPage`、`FormPage`、`AppDateTimePicker`；Vuexy `wizard-examples/create-deal.vue`、`AppStepper` | 增加新建差旅表单，保存走批次 mock；自动匹配仍保留为后续接口 | 设计阶段标注 v1.0，但当前页面可先完成出差前申请 | 列表筛选、人工新建和状态查看可用；自动匹配待后续接口 |
| 费用标准 | EX07 分支 | `ListPage`、`FormDrawer`；Vuexy tables/data-table | 增加 `编辑标准` `FormDrawer`，保存调用专用 mock 更新 | 原页面只读，缺少维护上限操作 | 列表、筛选和人工编辑可用 |
| 总账与报表 | F23–F27 分支 | `ListPage`、`MoneyText`、`StatusChip`；Vuexy tables/simple-table | 保留领域专属来源链接和订单→凭证规则卡，状态/金额统一复用业务组件；F24 增加借贷平衡提示 | 规则选择、来源追溯和余额校验不能由通用列渲染猜测 | 期间筛选、来源追溯、平衡校验、利润凭证生成可用 |
| 期末结账 | F28 分支 | `ListPage` 的检查清单 + Vuetify `VAlert`；Vuexy `form-wizard-numbered`/`AppStepper` | 保留清单式列表并使用现成分页/状态壳，结账按钮走服务层 | 结账是逐期间检查动作，`FormPage` 单一保存语义不适合多行检查项 | 未审批凭证时拒绝；检查通过后人工点击结账 |
| 成本结转/汇兑重估 | F29、F32 分支 | `ListPage`、`MoneyText`、`StatusChip` | 保留领域操作按钮，生成凭证统一走 API | 生成草稿需要行级期间/重估 ID | 预览、生成草稿和金额展示可用 |
| 预算与预算详情 | F30、F31 分支 | `ListPage`、`DetailPage`、`MoneyText`、`KpiCard` | 保留预算进度专属 KPI；详情时间线接审计接口，调整走保存动作 | 使用率、预警和调整记录是页面特有业务块 | 80% 预警、详情、人工调整和审计记录可用 |
| VAT/出口退税 | F33、F34 分支 | `ListPage`、`StatusChip`、`MoneyText`；Vuexy invoice list/file input | 保留列表字段专属渲染，移除通用页外的重复表格 | 当前接口是跟踪查询，状态和金额需要业务字典 | 期间筛选、状态、税额/退税额展示可用；资料上传待后端接口 |
| AgentCard、RecordDrawer、AssistantDrawer | 批次 A 全部页面 | 项目现成组件 | 未引入；AI 仅使用现有 `useAiModeStore` 提示/预填，审计记录放入 `DetailPage` 时间线 | 设计对批次 A 的 AI 是 L1/L2 建议，不能增加独立对话或写入口；详情记录不适合只读抽屉 | AI 关闭时人工路径仍可用，AI 不绕过审批 |
| 凭证列表/详情与利润页 | `pages/finance/vouchers/*`、`pages/finance/profit/*` | `ListPage`、`DetailPage`、`MoneyText`、`StatusChip` | 保留领域专属分录/来源追溯，期间选择和审批动作接 `api/gap-a` | 凭证分录、借贷平衡和来源链接不是通用 CRUD 字段 | 草稿→审批→批准护栏、来源追溯和利润期间选择可用 |

### Gap A 补齐复查（2026-11-10）

| 新增交互 | 复用组件/来源 | 保留专用代码的原因 | 追溯与状态 |
|---|---|---|---|
| EX06 差旅匹配 | `GapAPage` + `ListPage` + `FormPage` + `MoneyText` + `VDialog` | 匹配候选需要展示代码规则、分数和人工确认，无法由通用列表列渲染表达 | `src/api/gap-a.ts` 调用 mock；提交、建议、确认均追加审计 |
| F34 资料登记 | `FormDrawer` + Vuetify `VFileInput`/`AppSelect` + `StatusChip` | 只登记元数据且按三种资料类型做齐全校验，业务字段是退税专属 | 不保存文件内容；上传和校验状态写审计 |
| F33 模拟申报 | `ListPage` + `AppSelect` + `StatusChip` | 期间筛选由通用列表外的页面级查询条件驱动，申报动作是行级税务专属行为 | 期间作为 API 参数；保存模拟申报追加审计 |

批次 A 页面仍通过 `src/api/*.ts` 访问服务层，金额继续使用 `MoneyText` 展示；未新增 AI 对话界面，AI 关闭时上述人工路径完整可用。

### 批次 A 增量审计（`d0946a4..f548479`，2026-11-10）

本节复核本批补齐与两轮修复的实际代码，不以改动行数代替逐项检查。

#### 1. Vuexy / biz 组件复用

| 交互或区块 | 复用情况 | 理由与处理 |
|---|---|---|
| EX06 差旅列表、新建表单 | **已复用** `ListPage`、`FormPage`、`AppDateTimePicker`、`MoneyText`、`StatusChip` | 列表分页/筛选/列插槽由 `ListPage` 承担；表单壳由 `FormPage` 承担；金额和状态没有页面自写格式化或标签。 |
| EX06 匹配建议 | **保留专用** Vuetify `VDialog`，内部仍复用 `MoneyText` | 弹窗展示候选报销、规则、分数并等待人工确认，属于带业务内容的审阅视图；没有另写抽屉、确认组件或状态标签。 |
| F33 VAT | **已复用** `ListPage`、`AppSelect`、`StatusChip`、`MoneyText` | 期间筛选是页面查询条件，行级“保存模拟申报”调用 API；没有自写表格或金额格式化。 |
| F34 出口退税 | **已复用** `ListPage`、`FormDrawer`、`AppSelect`、Vuetify `VFileInput`、`StatusChip`、`MoneyText` | 抽屉、文件选择、状态和金额均使用现成组件；只登记文件元数据，不重复实现上传组件。 |
| EX03 报销明细 | **复用** `DetailPage`、`PermissionGate`、`MoneyText`；保留 Vuetify `VTable` | 明细行是凭证/审批专属字段，和列表分页列语义不同；表格没有复制分页、筛选、状态或金额组件。 |
| 其他批次 A 列表、详情、抽屉 | **已复用** `ListPage`、`DetailPage`、`FormDrawer`、`KpiCard`、`StatusChip`、`PermissionGate` | 未新增 `.vue` 通用组件；页面只做字段、插槽和 API 编排。 |

**组件结论：** 本批没有发现可安全一对一替换的重复通用表格、抽屉、确认框、金额组件或状态标签；因此没有代码级复用重构，已改内容仅在上一轮补齐中完成并由本节复核。

#### 2. `GapAPage.vue` 业务动作与追溯

| 功能 | API / mock 路径 | 实质检查 | 结论 |
|---|---|---|---|
| EX06 创建、提交、匹配建议、人工确认 | `src/api/gap-a.ts` → `mocks/services/gap-a.ts` | 保存状态、确定性规则（人员/日期窗口/预算）、人工确认、幂等拦截和审计追加均在服务层完成。 | **复用且可追溯** |
| F33 模拟申报 | `fetchGapAVat(period)`、`submitGapAVat(id)` | 期间作为 API 参数；状态由 `draft/ready` 到 `submitted`，重复提交拒绝，审计记录包含期间。 | **复用且可追溯** |
| F34 资料登记、资料校验 | `uploadGapARebateDocument(id)`、`validateGapARebate(id)` | 只存文件名、类型、大小；重复资料、后续状态上传和资料齐全校验均在 mock 服务层，动作追加审计。 | **复用且可追溯** |
| 既有报销、借款、凭证、结账、预算和重估动作 | 各自 `src/api/gap-a.ts` 写接口 | 页面没有直接写 mock 状态；按钮由 `run()` 调 API 后重新加载。 | **通过** |
| AI 识别并预填 | `identifyReceipt()` | 只在前端填充演示字段，不写数据库、不追加审计；明确标为只读演示建议，不伪装成真实识别接口，也不属于写动作。 | **通过**：AI 关闭时人工填写路径完整可用。 |

#### 3. 写接口权限、身份、审批和幂等

- `src/api/gap-a.ts` 的所有写函数均先调用 `assertCan()` 或 `assertAny()`；独立脚本逐项验证 viewer 越权均在接口层拒绝。
- 创建报销和差旅时由服务层 `actorId()` 适配器写入稳定 `claimantId`，凭证创建写入 `createdById`；审批自审和差旅匹配均按稳定 ID 判断，没有按显示名回退。报销审批顺序、凭证 `draft → pending`、重复提交/重复生成/已结账拦截均有服务层护栏。
- 所有批次 A 写动作均经 API 层进入 mock 服务并追加带 `actorId` 的审计；种子审计也补齐稳定 ID。
- `savePolicy()` 和 `closePeriod()` 均追加带期间/科目/限额或检查结果的审计事件；EX07 借方科目只能从 `EXPENSE_ACCOUNT_MAPPINGS` 选择。

#### 4. 报销科目映射与凭证来源

- 默认映射唯一来源是 `src/mocks/config/gap-a-expense-accounts.ts` 的 `EXPENSE_ACCOUNT_MAPPINGS`，每条配置和 EX07 提示均标注“示例映射，待会计核实”；报销凭证按费用类别取费用科目，贷方为 `其他应付款-员工`，没有沿用销售结算的 `主营业务成本 / 平台结算清算`。
- EX07 抽屉通过 `AppSelect` 展示 `EXPENSE_ACCOUNT_MAPPINGS` 的借方科目；服务层再次校验配置集合，保存后的科目不会脱离示例映射。提示继续标注“示例映射，待会计核实”。

#### 5. 金额确定性与地基契约

- 新增金额输入走 `minorFromDecimal()`；列表、详情和匹配建议的金额展示走 `MoneyText`，服务层金额使用万分位整数，独立脚本验证报销凭证借贷相等且金额等于明细金额。
- `GapAPage.vue` 的 KPI/提示金额使用 `MoneyText` 或现有格式化函数；服务层预算预警使用配置化 basis points 与 `percentOf()`，审计金额使用 `minorToDecimal()`，还款幂等使用借款状态/还款记录。
- `src/api/mock-client.ts` 地基文件保持不变；批次 A 内部统一通过 `actorId()` 适配器取稳定身份，后续可无缝对接批次 C 的 `userId` 契约，未回退到显示名。

#### 6. 验证证据与本轮变更

- `pnpm run typecheck`：通过。
- `node_modules\\.bin\\eslint.cmd . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx`：0 error，23 个既有 warning。
- `pnpm run build`：通过；构建后已恢复 `auto-imports.d.ts`、`components.d.ts`、`typed-router.d.ts`。
- 独立脚本 `%TEMP%\\cx-pw\\xbatch\\xa.ts`、`xa2.ts` 均复制到 `scripts\\_x*.ts` 后用 `pnpm exec tsx` 运行：均为 `== FAIL 0`；临时文件已删除，断言未修改。

### 批次 A 第四轮修复（2026-11-10）

对应提交：`fix(frontend): 批次 A 科目配置约束、写动作审计与稳定身份`

本轮已修复前述科目配置、写动作审计、稳定身份、金额确定性和还款幂等问题；页面金额继续复用现有 `MoneyText`/格式化能力，未修改批次 C 的 mock-client 地基文件。AI 预填继续是只读演示建议，不写状态，因此不产生写审计；这不是写动作遗漏。

### 批次 A 增量复用审计（`bc0fde0..092541b`，第二轮，2026-11-10）

本轮逐项复核范围内的改动文件：`src/components/biz/GapAPage.vue`、`src/mocks/services/gap-a.ts`、`src/types/gap-a.ts`，并对照 `src/api/gap-a.ts`、权限表和金额工具。当前工作树只恢复了构建生成的 `.d.ts` 文件，没有改动功能代码。

#### 1. 组件与金额复用

- `GapAPage.vue` 继续复用 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`MoneyText`、`StatusChip`、`PermissionGate`；费用科目下拉直接使用 `EXPENSE_ACCOUNT_MAPPINGS` 和现成 `AppSelect`，没有新增通用表格、抽屉、确认框或金额组件。
- 差旅匹配的 `VDialog` 仍保留为业务专用审阅弹窗：它同时展示候选报销、规则和分数并等待人工确认，现有 `useConfirm` 只提供二选一确认，不能一对一替换；弹窗内部金额仍使用 `MoneyText`。
- 页面显示金额改由 `minorToDecimal`、`toDisplay`、`formatMoney` 或 `MoneyText` 处理；服务层预算预警使用整数万分位和 `percentOf`，未发现新增金额浮点计算。**[建议修改]** `savePolicy`、`saveBudget`、`repayLoan`、`createTrip`、`createClaim` 的服务边界仍只检查 `<= 0`，没有统一的 `Number.isFinite`/`Number.isSafeInteger` 校验；当前页面调用均先经 `minorFromDecimal`，但直接调用 API 仍可能写入非整数最小单位。

#### 2. 写接口、身份、审批和幂等

- `src/api/gap-a.ts` 的写函数均先调用 `assertCan` 或 `assertAny`，创建报销/差旅使用 `session.userId`，审批自审和差旅匹配按 `claimantId`/`actorId` 比较；`savePolicy` 也在服务层限制借方科目必须来自配置集合，属于有效的服务层复核。
- 新增 `audit()` 事件带当前 `actorId`，本轮种子凭证审计也补齐了稳定 ID。
- **[必须修复] 审批存在跳级和同人完成两级的问题。** `decideGapAClaim` 只调用通用 `assertCan('approve')`，服务层按调用者传入的 `step` 执行；没有把 `manager`/`finance` 步骤绑定到对应角色或权限，也没有禁止同一个审批人连续处理两步。因此有 `approve` 权限的财务角色可以直接请求主管步骤，再请求财务步骤，绕过职责分离。建议在 API/服务层按步骤检查角色/权限，并拒绝与前一步相同的 `actorId`。
- **[必须修复] 旧 `localStorage` 数据没有稳定身份迁移。** `loadState()` 对旧 claims/loans/trips 只做浅复制，没有补回 `claimantId`；对 `audits` 及 voucher timeline 也没有补回 `actorId`。旧记录因此可能在 `item.claimantId` 为空时绕过自审检查，差旅匹配也无法按稳定身份过滤，历史审计仍缺操作人 ID。建议做显式版本迁移，无法确认身份时拒绝审批/匹配并标记待人工修复。
- **[建议修改] 部分动作不是幂等的。** `suggestTripClaim()` 每次重复调用都会新增一条匹配建议审计，`validateRebate()` 每次重复校验也会新增审计；若要求重试安全，建议使用稳定动作键或已有结果直接返回。还款去重依赖新增的 `repaymentAmounts`，旧数据未迁移时仍可能重复登记同一金额。
- **[必须修复] 页面角色与写权限不一致。** `EX07`、`F33`、`F34` 等页面把 `finance` 列为可见角色，但对应写 API 使用 `assertCan('update')`；`legacyRoleActions.finance` 没有 `update`，因此财务用户可看到编辑/申报/资料按钮却必然被接口拒绝。F23 的收入凭证生成同样使用 `create`，而财务角色没有 `create`。应统一页面可见角色、按钮门控和 API 所需权限，避免误导并确保有效权限模型一致。

#### 3. 结论

组件复用和金额展示方向符合现有地基，未发现可以安全一对一替换的通用 UI。科目配置约束、稳定 ID 写入和新增审计字段在新鲜状态下有效；但上述审批职责、旧状态迁移、幂等和角色权限问题会影响安全或实际写入路径，不能按“本轮全部通过”记录。按任务要求本轮只提交本审计文档，未擅自扩大功能修复。

#### 4. 本轮验证

- `pnpm run typecheck`：通过（退出码 0）。
- `node_modules\\.bin\\eslint.cmd . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx`：通过（退出码 0，0 errors、23 个既有 warnings）。

### 批次 A 第五轮修复（2026-11-10，1935bc1 审计问题）

本轮已关闭前一节列出的三项「必须修复」：

- **审批职责分离：已修复。** `manager`/`finance` 使用独立的有效权限点，服务层和 API 层都检查；审批步骤按顺序推进，提交人不能自审，同一 `actorId` 不能连续完成两级，重复审批拒绝。
- **旧 localStorage 身份迁移：已修复。** 状态版本升级为 2，迁移 claims/loans/trips、审批步骤、voucher timeline 和业务审计的稳定身份；无法映射的记录标为 `needs_manual_repair`（待人工修复），审批与差旅匹配均拒绝继续。
- **页面写权限一致性：已修复。** EX07、F30、F33、F34、EX04、F23 的写 API 改用对应细粒度权限；财务获得设计允许的费用标准、借款、预算、VAT、出口退税和财务审批权限，其他角色未放宽；无权限按钮禁用并给出提示。

服务层金额入口统一拒绝非 `Number.isSafeInteger` 或不大于零的最小单位金额。独立验收脚本 `xa.ts`、`xa2.ts` 已覆盖职责分离和非整数金额，均为 `== FAIL 0`；另以临时迁移断言验证未知身份记录的待人工修复护栏。

## 补齐批次 B 独立复用审计

审计范围：相对 `3f325c0` 的全部 `frontend` 变更，重点为 `src/views/gap-b/GapBPage.vue`、批次 B 路由薄壳、`src/api/gap-b.ts`、`src/types/gap-b.ts` 和 `src/mocks/services/gap-b.ts`。对照项目 `src/components/biz/*`、Vuexy full-version 的 `src/@core/components`、`src/components/dialogs`、`src/views/**`、`src/pages/**`，以及 Vuetify 组件。

| 组件 / UI 块 | 位置 | 现成等价物 | 处理 | 原因 | 业务操作是否满足 |
| --- | --- | --- | --- | --- | --- |
| 批次 B 通用页面壳 | `src/views/gap-b/GapBPage.vue` | `ListPage`、`DetailPage`、`FormPage` | 保留为薄组合 | 只负责根据 `pageKey` 选择 API 数据和业务插槽，列表、详情、表单外壳均来自项目共享组件。 | 是，已逐页补齐创建、详情和提交动作 |
| 加载状态 | `GapBPage.vue` | `components/biz/LoadingState.vue`、Vuexy skeleton | 已替换 | 删除页面内重复的 `VSkeletonLoader`，统一加载文案和骨架。 | 是 |
| S09 询价列表与新建 | `pages/procurement/rfqs.vue`、`GapBPage.vue` | `ListPage`、`FormDrawer`、`PermissionGate` | 已替换并补齐 | 新建询价改为现成抽屉和创建权限门禁；列表仍复用筛选、分页、导出。 | 是：列表、新建询价、人工发送前草稿 |
| S10 询价比价 | `pages/procurement/rfqs/[id].vue`、`GapBPage.vue` | `DetailPage`、`MoneyText`；Vuexy invoice editable / `VCard` | 保留业务专属报价卡 | 并排报价、含税总额和人工选定供应商是比价专属结构，`AppPricing.vue` 是订阅套餐数据，不能直接套用。 | 是：查看报价、人工选定并生成采购单草稿 |
| S11 采购合同列表 | `pages/procurement/contracts.vue` | `ListPage`、`StatusChip` | 保留 | 仅提供合同筛选、状态和详情入口，没有另写表格。 | 是：列表、筛选、进入详情 |
| S12 合同详情 | `pages/procurement/contracts/[id].vue` | `DetailPage`、`VTable`、`VFileInput` | 已补齐 | 复用详情时间线和关联采购单；价格表与附件是合同字段专属，使用 Vuetify 直接组件。 | 是：条款、价格表、附件入口、关联采购单 |
| S13 供应商评估 | `pages/procurement/supplier-scores.vue` | `ListPage`、`KpiCard`、`StatusChip` | 已补齐 | 通过 `ListPage#widgets` 接入项目 KPI 薄封装，评分仍由代码提供。 | 是：列表、筛选、平均评分 |
| I12 批次与效期 | `pages/inventory/batches.vue` | `ListPage`、`StatusChip` | 保留 | 直接复用共享列表和状态字典，临期状态来自服务层。 | 是：列表、筛选、状态查看 |
| I13 补货建议 | `pages/inventory/replenishment.vue` | `ListPage`、`PermissionGate` | 保留并补齐人工路径 | AI 起草按钮受 AI 开关控制；AI 关闭时保留手动新建采购单入口。 | 是：建议列表、AI 起草、人工起草 |
| I14 调拨详情 | `pages/inventory/transfers/[id].vue` | `DetailPage`、`PermissionGate`、`VStepper` | 已补齐 | 在详情页新增确认调拨动作，库存流水说明继续使用步骤条。 | 是：调出 / 在途 / 调入确认 |
| I15 盘点详情 | `pages/inventory/counts/[id].vue` | `DetailPage`、`PermissionGate`、`AppTextField` | 已补齐 | 增加实盘数量录入和差异审批提交，过账状态仍由 mock 服务层更新。 | 是：逐行录入、查看差异、提交审批 |
| D05 业务链追溯 | `pages/dashboard/chain.vue` | `DetailPage`、Vuexy timeline | 已替换 | 删除页面内自写 `VTimeline`，改用 `DetailPage` 右栏时间线；搜索和断点数据保持原动作。 | 是：输入单号、查看 5 段链路和 4 个已接通断点 |
| INT01 导入向导 | `pages/integrations/import-wizard.vue` | `FormPage`、Vuetify `VStepper`/`VFileInput`/`VTable` | 保留并补齐 | Vuexy `DropZone.vue` 限定图片预览，不适合 CSV/XLSX；映射表和导入预览需要逐行选择 / 展示，Vuetify 表格是直接等价物。 | 是：来源、上传、映射确认、预览、导入 |
| INT02 平台同步 | `pages/integrations/sync-jobs.vue` | `ListPage`、`StatusChip`、`PermissionGate` | 保留并补齐 | 同步任务表和立即同步按钮分别复用列表与更新权限门禁。 | 是：任务状态、失败信息、立即同步 |
| INT03 金蝶设置 | `pages/integrations/kingdee.vue` | `FormPage`、`AppTextField`、`AppSelect` | 已补齐 | 将账套、凭证字、导出格式和科目对照字段拆为现成表单控件。 | 是：配置并保存 |
| INT04 ERPNext 账套 | `pages/integrations/erpnext.vue` | `FormPage`、`AppTextField`、`AppSelect` | 已补齐 | 使用现成表单控件表达站点、服务地址和审批后推送策略。 | 是：配置并保存 |
| INT05 集成日志 | `pages/integrations/logs.vue` | `ListPage`、`StatusChip`、`MoneyText` | 保留 | 日志是只读列表，通用列表已覆盖筛选、分页和导出。 | 是：查看导入、同步、导出结果 |
| W08 IM 审批卡片 | `pages/approvals/im-preview.vue` | `ListPage`、`RecordDrawer`、`StatusChip`、`MoneyText`、Vuexy card pattern | 已替换并补齐 | 增加只读卡片抽屉、批准 / 驳回；超过门槛继续只显示网页确认，保留内容变化校验。 | 是：查看、批准、驳回、网页确认、篡改提示 |
| SYS19 渠道绑定 | `pages/account/channel-bindings.vue` | `DetailPage`、`ListPage`、`PermissionGate` | 已替换 | 用详情壳承载绑定列表，绑定和解绑由权限门禁包裹。 | 是：查看、绑定、解绑 |
| SYS20 IM 审批设置 | `pages/admin/im-approval.vue` | `FormPage`、`ListPage`、`StatusChip` | 已补齐 | 表单覆盖通道、审批类型、金额门槛、回调和签名状态，侧栏列表展示全员通道配置。 | 是：启停配置、门槛、回调、签名状态、绑定概览 |
| SYS25 通知渠道 | `pages/admin/channels.vue` | `ListPage`、`StatusChip`、Vuexy notification settings | 已补齐 | 启用开关改为可操作更新，保留测试发送和新增渠道入口。 | 是：查看、启用 / 停用、测试发送、新增 |
| SYS26 新增渠道 | `pages/admin/channels/new.vue` | `FormPage`、`AppSelect`、`AppTextField`、`VSwitch` | 已补齐 | 增加测试发送和创建后启用开关；密钥只显示配置提示，不回显值。 | 是：选择插件、填写配置、测试发送、启停 |
| AI 建议块 | `GapBPage.vue` 的 I13 操作区 | 全局 `AssistantDrawer` 的 `AgentCard` 协议、`PermissionGate` | 保留薄按钮入口 | 当前仓库没有独立 `AgentCard.vue`；AI 只提交建议，写操作仍由人工确认，关闭 AI 时人工入口可用。 | 是，AI 关闭后人工路径可用 |
| 权限、数据、审计与 i18n 契约 | `src/config/permissions.ts`、`src/types/gap-b.ts`、`src/api/gap-b.ts`、`src/mocks/services/gap-b.ts` | 项目权限引擎、API mock 出口、Vuexy i18n | 保留 | 这些是数据契约和权限点，不是可替换 UI；未改权限地基。 | 是，动作仍经统一服务出口 |

审计结论：本批没有新增通用 UI 组件。`GapBPage.vue` 保留为业务差异的薄组合；列表、详情、表单、抽屉、状态、金额、权限门禁和 KPI 均接入现成实现。补齐前发现的缺口（盘点提交、调拨确认、IM 驳回、渠道启停 / 测试、合同价格表 / 附件、金蝶 / ERPNext 字段）已在本批补上；未保留只展示而无对应设计动作的页面。



## 补齐批次 B 缺口复查（本轮）

复查范围：`src/views/gap-b/GapBPage.vue`、`src/mocks/services/gap-b.ts`、采购退货 mock、订单/CRM/物流关联投影，以及批次 B 路由冲突修复。继续复用 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`StatusChip`、`MoneyText`、`PermissionGate`、Vuetify `VStepper`/`VTable`，没有新增通用组件。

| 缺口 | 复用与实现 | 审计/可追溯验证 |
| --- | --- | --- |
| 订单客户/商机双向链接 | 订单详情、CRM 客户/商机详情继续使用 `DetailPage` 的关联单据区和 Vuetify `VBtn` | `customerId`、`opportunityId` 来自 mock 数据；赢单动作写审计 |
| 采购退货明细、负数流水、应付冲减 | 既有采购退货 `ListPage` + `RecordDrawer`；明细使用 `VAlert`/`MoneyText` | 确认动作调用库存服务，写负数 movement、更新应付并写审计 |
| 发货运单/头程双向链接 | 订单详情复用 `DetailPage` 关联单据和 `VBtn` | 物流/头程节点可打开运单，订单关联回运单 |
| 补货、询价、调拨、盘点、导入、渠道 | 统一批次 B 页面壳；步骤表单使用现成 `FormPage`/`VStepper`/`VFileInput` | 每个保存/审批/启停动作经 `src/api/gap-b.ts`，mock 服务追加审计 |

本轮没有把静态 mock 误写成真实后端能力；真实文件、外部 IM 回调、ERPNext/金蝶连接仍按报告标为未接入。

## 批次 B 增量复用审计（第二轮）

审计范围：`c643461..3e88c5a` 中的前端页面、API、mock 服务和共享种子，重点检查 `GapBPage`、采购退货、库存调拨/盘点、订单与 CRM 关联，以及 `3e88c5a` 的 `mocks/seed/build.ts`。本轮只追加审计结论，没有扩大功能代码改动。

### 组件和 API 复用

- `GapBPage.vue` 继续复用 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`StatusChip`、`MoneyText`、`PermissionGate`、`LoadingState` 和 `KpiCard`。询价比价、合同价格表、导入映射、库存步骤和业务链卡片是字段/流程专属布局，保留 Vuetify `VCard`、`VTable`、`VStepper`、`VFileInput` 属于安全的一对一复用范围。
- 采购退货页面复用 `ListPage`、`RecordDrawer`、`FormDrawer`、`StatusChip`、`MoneyText`、`PermissionGate` 和 `useConfirm`；订单、CRM 客户/商机详情复用 `DetailPage`、`MoneyText` 和既有 API 出口。没有新增通用 `.vue` 组件，也没有页面直接绕过 `src/api` 调 mock 服务。
- `submitGapBAction` 对已知动作做 `assertCan` 权限映射；库存、采购退货和 CRM 写 API 也在 API 层取得当前角色后再进入 mock 服务。权限门禁满足演示原型的入口控制，但服务函数本身仍接收可直接调用的 `Actor`/payload，后端接入时需把权限校验和动作白名单下沉到真实服务边界。

### 写入、审批和审计检查

| 检查项 | 结论 |
| --- | --- |
| 稳定 userId | `useSessionStore().userId` 按演示角色映射到稳定 ID；当前 actor 会保留该 ID，盘点、IM 和采购审批均按 ID 判断。 |
| 防自审 | I15、W08 IM 和采购单服务层均记录提交人 ID，并拒绝提交人批准/驳回自己的事项；另一身份可以继续审批。 |
| 防跳级 | API 动作映射和 `applyGapBAction` 服务入口都按有效权限与动作白名单校验，未知动作和直接绕过 API 的越权调用均被拒绝。 |
| 幂等 | 调拨、盘点、导入、IM 审批等状态迁移重复调用会被状态检查拦截；询价、同步、渠道创建、附件保存、测试发送、链路查询和绑定/解绑没有请求幂等键，重复请求会新增记录或重复审计，不能判定为完整幂等。 |
| actorId 审计 | `Actor`、`AuditEvent`、`writeAudit`、批次 B `record()`、库存流水和采购服务均写入稳定 `actorId`；同名或角色切换仍可按 ID 追溯。 |

### 金额检查

金额计算路径总体使用 `utils/money` 的整数 `Minor`、`minorFromDecimal`、`addMinor`、`mulQty`，采购退货金额由采购行单价乘数量确定性计算，未发现使用 `float` 算钱的新增代码。

本轮已统一金额口径：IM 卡片、IM 门槛和询价金额均以“元”录入并通过 `minorFromDecimal()` 转为万分位 `Minor`；`MoneyText minor` 按同一单位展示，服务层不再使用 `threshold * 100` 或裸 `Number(payload.amount)`。

### 共享种子 VERSION 5 复核

已恢复 `3e88c5a` 父版本的月份分布并递增种子版本到 5 清理旧缓存。订单总数为 100，10 月利润快照行恢复为 19；独立断言复核仪表盘销售额 `1975.68 USD`、净利润 `639.64 USD`，未再发生共享金额漂移。旧基线 `NW-TENT-2P-OLV` 详情改为回退到最近有数据的 `2026-06`，页面明确标注“示例数据”并列出 4 个来源订单。

### 本轮结论

组件复用符合现有 Vuexy/Vuetify 薄封装约定，页面层没有发现适合安全一对一替换的重复通用组件。actorId、W08/采购单防自审、服务入口权限、金额 scale 和共享种子基线已闭合；建议类请求幂等键按本轮范围外保留。
## 补齐批次 C 独立复用审计

审计范围来自 git diff 3f325c0 --stat 的 frontend 文件：src/views/gap-c/GapCPage.vue、21 个批次 C 路由壳、src/api/gap-c.ts、src/mocks/services/gap-c.ts、src/types/gap-c.ts、页面/权限/导航/i18n 配置及本审计文档。参考了项目 src/components/biz/*、Vuexy full-version 的 src/views/** / src/pages/** / src/components/dialogs/**，以及 Vuetify 3.10。未读取 .env、密码文件或密钥。

### 自写组件和大段 UI 块

| 组件/UI 块 | 位置 | 现成等价物 | 处理 | 原因 | 业务操作是否满足 |
| --- | --- | --- | --- | --- | --- |
| 批次 C 通用编排视图 | src/views/gap-c/GapCPage.vue | 项目 ListPage/DetailPage/FormPage/FormDrawer/RecordDrawer；Vuexy src/pages/apps/user/list/index.vue、src/pages/apps/user/view/[id].vue | 已替换为薄编排 | 页面只保留 pageId 到数据/API 的编排；列表、详情、表单、抽屉由现成组件承载。 | 21 页均按设计入口提供列表、详情或编辑动作；AI 关闭后人工路径保留。 |
| 状态标签 | GapCPage.vue 的列表状态、详情结果 | 项目 src/components/biz/StatusChip.vue；Vuetify VChip 仅作无业务语义的敏感标记 | 已替换 | 统一状态字典和中英文颜色；原先按字符串手写颜色的 VChip 已删除。 | W05/W06 审批、SYS16 授权、SYS17 复核和 SYS23 有效权限均可读。 |
| 金额展示 | GapCPage.vue 审批/记录抽屉 | 项目 src/components/biz/MoneyText.vue | 保留并复用 | 金额来自 API 的 minor 单位，显示必须统一走 MoneyText，页面不计算金额。 | W05 建议金额和详情抽屉可读，人工批准/驳回可用。 |
| 权限显隐和写操作 | GapCPage.vue 的保存、审批、复核、临时授权按钮 | 项目 src/components/biz/PermissionGate.vue；utils/permission-engine.ts | 保留并补齐 | Vuexy/CASL 没有 CrossERP 的角色继承、拒绝优先和职责分离语义；服务层仍是最终拦截。 | 写按钮按 create/update/approve 显隐，AI 建议仍只能真人处理。 |
| AI 建议卡片/入口 | App.vue 的 AssistantDrawer 与 W05 顶部提示 | 项目 src/components/biz/AssistantDrawer.vue、AgentCard 类型和 Vuexy src/views/apps/chat/ChatLog.vue | 保留，不在 GapCPage 重写 | AgentCard 是全局助手的统一消息卡片协议；W05 业务审批详情用 RecordDrawer，避免复制聊天卡片。 | AI 开启可见建议摘要；AI 关闭时助手隐藏，W05 人工列表和审批抽屉仍可用。 |
| 列表、筛选、分页、列设置、CSV | GapCPage.vue 的 W05/W06/W07/N01/RP01/U05/U07/SYS14–18/SYS22/SYS24 | 项目 src/components/biz/ListPage.vue；Vuexy src/pages/apps/ecommerce/product/list/index.vue、src/pages/apps/user/list/index.vue；Vuetify VDataTableServer | 已替换/保留 | 所有列表统一接入关键字、状态/级别筛选、日期筛选、分页、列设置、CSV 和错误重试。 | 列表页操作满足；SYS22 还能编辑矩阵格并在保存前填写二次确认人。 |
| W05 智能体建议 | src/pages/approvals/agent-suggestions.vue → GapCPage page-id=W05 | ListPage + StatusChip + MoneyText + RecordDrawer；Vuexy KanbanCard.vue 仅作卡片参考 | 已替换并补齐 | 行点击和“查看并处理”打开只读建议快照；批准/驳回走 PermissionGate 和 API。 | 满足筛选、详情、批准/驳回、真人路径；AI 关闭仍可操作。 |
| W06 抄送我的 | src/pages/approvals/cc.vue → W06 | ListPage + RecordDrawer + StatusChip；Vuexy tables/data-table.vue | 已替换并补齐 | 抄送是只读列表，使用同一列表/详情壳，不复制表格。 | 满足状态/日期筛选、详情只读；不提供写操作符合设计。 |
| W07 审批规则与额度 | src/pages/approvals/rules.vue → W07 | ListPage + FormDrawer；Vuexy src/components/dialogs/AddEditPermissionDialog.vue / AppStepper.vue | 已替换并补齐 | 原列表没有编辑入口；现在每行可打开 FormDrawer 编辑级别、金额、审批人和 IM 开关。 | 满足列表筛选、编辑和保存；保存接口记录审计。 |
| N01 消息中心 | src/pages/notifications/index.vue → N01 | ListPage + StatusChip；Vuexy @core/components/Notifications.vue、src/apps/email/index.vue | 保留并补齐 | 通知专属已读动作保留为列表插槽，不另造消息表。 | 满足关键字/阅读状态/日期筛选、标为已读；AI 提醒可汇总。 |
| N02 我的订阅 | src/pages/notifications/subscriptions.vue → N02 | FormPage；Vuexy src/views/apps/ecommerce/settings/SettingsNotifications.vue、UserTabNotifications.vue | 已替换 | 原 VCard 表单改由 FormPage 统一标题、校验、保存/取消操作。 | 满足四渠道开关编辑和保存；不依赖 AI。 |
| RP01 报表中心 | src/pages/reports/index.vue → RP01 | ListPage；Vuexy src/pages/cards/card-advance.vue、apps/academy/dashboard.vue | 保留并复用 | 报表目录使用统一列表，行点击进入具体报表。 | 满足搜索/分页/CSV 和进入详情。 |
| RP02 报表查看 | src/pages/reports/[id].vue → RP02 | DetailPage + KpiCard + Vuetify VTable；Vuexy src/pages/components/expansion-panel.vue、charts/apex-chart.vue | 已替换并补齐 | 原 VCard 改为详情壳；增加汇总 KPI、期间运行、结果筛选和 CSV 导出。 | 满足运行、筛选、导出；数字只展示 API 结果。 |
| RP03 自定义报表 | src/pages/reports/builder.vue → RP03 | FormPage；Vuexy src/forms/form-wizard-icons.vue、AppSelect/AppAutocomplete | 已替换 | 原短表单改为 FormPage，报表名有必填校验，保存/取消统一。 | 满足新建/保存；数据源字段仍由批次 C mock/API 协议提供。 |
| U05 AI 操作日志 | src/pages/audit/ai/index.vue → U05 | ListPage + StatusChip；Vuexy src/tables/data-table.vue | 保留并复用 | 审计表字段是专属数据，列表壳统一。 | 满足筛选、日期、CSV、点击进入 U06；审计行来自 fetchGapCAudit。 |
| U06 建议追溯 | src/pages/audit/ai/[id].vue → U06 | DetailPage + VTimeline；Vuexy src/pages/components/timeline.vue、expansion-panel.vue | 保留并复用 | 时间线字段是建议追溯的业务专属内容，详情壳和时间线已复用。 | 满足问题→步骤→结果详情；只读，无写动作。 |
| U07 敏感操作告警 | src/pages/audit/alerts.vue → U07 | ListPage + RecordDrawer + PermissionGate；Vuexy src/tables/data-table.vue、pages/components/alert.vue | 已替换并补齐 | 原列表处理按钮之外增加行详情抽屉，解决“只展示不查看详情”。 | 满足级别/日期筛选、详情、标记已处理和审计记录。 |
| U08 日志保留与归档 | src/pages/audit/retention.vue → U08 | FormPage；Vuexy src/views/apps/ecommerce/settings/SettingsCheckout.vue | 已替换 | 原 VCard 表单改由 FormPage 承载保存/取消。 | 满足保留年数、归档等待天数编辑和保存；追加不可删除提示保留。 |
| SYS14 字段权限 | src/pages/admin/field-permissions.vue → SYS14 | ListPage + AppSelect；Vuexy src/apps/permissions/index.vue、forms/checkbox.vue | 保留并复用 | 字段级四态访问值使用现成列表插槽；服务层负责字段裁剪。 | 满足筛选、逐行编辑和保存，权限点不变。 |
| SYS15 数据范围 | src/pages/admin/data-scopes.vue → SYS15 | ListPage + AppSelect；Vuexy src/apps/roles/index.vue、views/apps/roles/UserList.vue | 保留并复用 | 范围枚举是业务专属，控件通过列表插槽复用。 | 满足关键字、逐行范围编辑和保存。 |
| SYS16 临时授权 | src/pages/admin/temp-grants.vue → SYS16 | ListPage + FormDrawer；Vuexy src/tables/data-table.vue、src/views/apps/user/list/AddNewUserDrawer.vue | 已替换 | 删除原手写 VTable/VCard；列表、状态筛选和新增表单分别由共享组件承载。 | 满足列表筛选、新建、到期状态显示；服务层自动收回并记录审计。 |
| SYS17 权限复核 | src/pages/admin/access-reviews.vue → SYS17 | ListPage + RecordDrawer + StatusChip；Vuexy src/apps/user/list/index.vue | 已替换并补齐 | 行详情和确认复核集中在记录抽屉，列表不复制详情布局。 | 满足状态/截止日期筛选、详情、确认复核和审计。 |
| SYS18 职责分离 | src/pages/admin/sod-rules.vue → SYS18 | ListPage + Vuetify VSwitch；Vuexy src/tables/simple-table.vue | 保留并复用 | 只有逐行启停这一项业务动作，列表插槽足够。 | 满足筛选、启停保存；职责分离由服务层拦截审批。 |
| SYS21 角色详情 | src/pages/admin/roles/[id].vue → SYS21 | DetailPage + StatusChip + Vuexy roles 视图 | 已替换 | 原 VCard 改为 DetailPage；复制动作放到详情 actions 槽。 | 满足角色详情、继承/权限快照和复制草稿入口；实际落库仍待后续权限 API。 |
| SYS22 权限矩阵 | src/pages/admin/permission-matrix.vue → SYS22 | ListPage + AppSelect + PermissionGate；Vuexy src/apps/permissions/index.vue、src/tables/data-table.vue | 已替换并修复分支 | 原可编辑 VTable 分支被 isList 遮住；现在由 ListPage 正常渲染 effect 插槽、批量保存和二次确认。 | 满足矩阵筛选/编辑、保存前确认、保存后权限变更记录。 |
| SYS23 有效权限查看 | src/pages/admin/effective-permissions.vue → SYS23 | DetailPage + StatusChip；Vuexy src/pages/apps/user/view/[id].vue、pages/components/expansion-panel.vue | 已替换 | 原 VCard 改为详情壳，用户选择和结果状态复用业务组件。 | 满足选择用户、查看来源/拒绝原因；只读符合设计。 |
| SYS24 权限变更记录 | src/pages/admin/permission-changes.vue → SYS24 | ListPage；Vuexy src/tables/data-table.vue、timeline.vue | 保留并复用 | 改前/改后/确认人是审计专属列，列表壳统一。 | 满足关键字、日期、CSV 和审计记录查看。 |
| 21 个路由壳 | src/pages/admin/**、approvals/**、audit/**、notifications/**、reports/** | GapCPage + Vue Router 文件路由；Vuexy 页面路由结构 | 保留为薄壳 | 路由文件只传固定 pageId，不重复写页面 UI、API 或权限逻辑。 | 路由、权限点、data-test 和 i18n 入口保持不变。 |
| API、mock、类型、配置支撑 | src/api/gap-c.ts、src/mocks/services/gap-c.ts、src/types/gap-c.ts、config/pages.ts、config/permissions.ts、navigation/build-nav.ts、plugins/i18n/ui.ts、声明文件 | 无可替换 UI；沿用现有 src/api/Pinia/权限引擎协议 | 保留 | 这些文件不是组件；替换会破坏路由、权限、数据中心、审计和 i18n 约束。 | API/mock 写操作继续做权限校验并写审计；前端只消费类型化数据。 |

### 独立结论

- 本批没有新增通用组件；所有新增业务 UI 都集中在已有 GapCPage.vue 编排，并已接入项目业务地基。
- 已实际替换的重复实现：状态字符串 VChip → StatusChip；N02/RP03/U08 的 VCard 表单 → FormPage；RP02 的 VCard → DetailPage + KpiCard；SYS16 的 VCard/VTable → ListPage + FormDrawer；SYS21/SYS23 的 VCard → DetailPage；SYS22 遮挡的手写矩阵 → ListPage 编辑插槽；W05/W06/U07/SYS17 补上 RecordDrawer 详情和动作。
- 保留的 Vuetify VTable 只出现在订阅渠道开关、报表结果、AI 追溯和有效权限等字段专属块；它们被 FormPage/DetailPage 包住，没有重新实现通用筛选、分页或抽屉。
- AI 关闭时 App.vue 隐藏 AssistantDrawer，但 W05 的 ListPage、RecordDrawer、PermissionGate 和人工批准/驳回 API 路径仍可用。
- 真实后端 /api/v1、真实数据库审计链和真实角色数据仍未接入；本批只验证静态前端与 mock 服务，相关事实标为“未验证”。

### 批次 C 缺口补齐复用审计

本轮继续以 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`PermissionGate`、`StatusChip` 和 `KpiCard` 为 UI 边界。SYS21 的复制表单复用 `FormDrawer`，RP03/U08 继续复用 `FormPage`，权限矩阵和字段/范围表继续复用 `ListPage` 的行插槽；没有新增通用组件。角色页原有页面可见性矩阵保留，并在顶部复用 `FormDrawer` 增加批次 C 角色复制入口。

新增的 `src/api/scoped-reads.ts` 与 `src/mocks/services/scoped-reads.ts` 只承载类型化 mock 读接口，页面仍只调用 `src/api/*`。数据范围和字段投影在服务层完成，页面不通过 CSS 隐藏敏感字段。`scripts/gap-c-scoped-reads.ts` 覆盖订单、报销和员工档案的部门/本人/无权限边界。

所有本批按钮均有可观察行为：保存会调用 API 并提示，角色复制和归档会写 mock 审计，报表构建器会保存并运行结果，矩阵会显示影响用户并执行二次确认；真实文件存储、外部接口和后端审计链仍标为“未验证”。

### 批次 C 第二轮增量复用审计（b1d45b9..6800112）

审计范围为本范围新增或改动的 frontend 文件：`src/api/scoped-reads.ts`、`src/mocks/services/scoped-reads.ts`、`src/mocks/services/gap-c.ts`、`src/utils/permission-engine.ts`、`src/types/gap-c.ts` 及对应独立检查脚本。范围内没有新增或改动 `.vue` 页面，因此没有新的页面级 UI 需要替换；既有 C 批次页面仍由上一节记录的 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`StatusChip`、`MoneyText` 和 `PermissionGate` 承载。本轮未读取 `.env`、密码文件或密钥，也没有启动预览或浏览器进程。

#### 增量核对结果

| 核对项 | 结论 | 证据 |
| --- | --- | --- |
| 页面/组件复用 | 通过 | 本范围无页面变更；新增范围读接口位于 `src/api/*` 和 mock service，未在页面复制权限或数据裁剪逻辑。 |
| 权限判断集中 | 通过 | `scopeAllows`、`shopsForSubject`、`projectGapCField` 统一调用 `effectivePermission` / `fieldAccess`；页面没有新增权限判断。 |
| 数据范围 | 通过 | `store` 必须有 `shopId` 且命中绑定，`self`/`owner` 必须命中 `ownerId`，`department` 必须命中主体部门；缺字段拒绝；多个范围按并集命中；`all` 明确允许缺关联字段。未知范围或空范围拒绝。 |
| 旧五角色基线 | 通过 | `xperm.ts` 报告旧页面差异 `0`；`check-legacy-read-apis.ts` 检查 102 个旧读接口，`== FAIL 0`；旧角色敏感薪资、证件、银行卡字段仍隐藏。 |
| 合法全公司授权 | 通过 | `xperm2.ts` 验证旧 `admin` 的订单、报销、员工集合覆盖所有主体可见集合，且 `admin` 成本/毛利为 `visible/visible`；旧 `finance` 报销集合与 `admin` 一致。 |
| 店铺范围与并集 | 通过 | `xperm3.ts` 验证缺 `shopId` 拒绝、他店拒绝、本人店铺允许；`operator` 的 `store ∪ owner` 语义成立；`== FAIL 0`。 |
| 金额 | 通过 | 本范围未引入金额计算；现有 mock 金额/工资值保持整数最小单位，展示仍由 `MoneyText`/`utils/money` 负责，未引入浮点计算或页面换算。 |
| 写接口 | 部分通过，见缺口 | 本轮没有新增写接口；现有审批决定接口仍经服务层有效权限校验，使用 session `userId` 防自审，金额超过 5000 的财务审批限制仍在，已处理状态阻止重复决定。 |

#### [必须修复] 审计记录没有持久化 actorId

`src/mocks/services/gap-c.ts` 的 `audit()` 从 `currentActor()` 取得 `userId`，但 `src/mocks/services/audit.ts` 的 `writeAudit()` 只写入 `actor` 显示名和 `actorRole`，`AuditEvent` 也没有 `actorId` 字段。这样同名用户无法可靠追溯，不能满足“审计带 actorId”的要求。该问题属于现有 mock 审计模型，本轮只记录，不扩大功能改动；后续应让审计事件保存稳定用户 ID，并让导出/查询沿用该字段。

另一个现有缺口是 `saveGapCMatrix()` 的二次确认人仍以可变显示名 `confirmer` 传入并比较，未使用确认人的稳定用户 ID；本轮没有改动该接口，保留给权限审计后续修复。

#### 本轮验收命令摘要

- `%TEMP%\\cx-pw\\xbatch\\xperm.ts`（复制到 `frontend/scripts/_xperm.ts` 执行后删除）：`== FAIL 0`，旧五角色页面差异 `0`。
- `%TEMP%\\cx-pw\\xbatch\\xperm2.ts`（复制到 `frontend/scripts/_xperm2.ts` 执行后删除）：`== FAIL 0`。
- `%TEMP%\\cx-pw\\xbatch\\xperm3.ts`（复制到 `frontend/scripts/_xperm3.ts` 执行后删除）：`== FAIL 0`。
- `frontend/scripts/check-legacy-read-apis.ts`（复制到 `frontend/scripts/_xcheck-legacy-read-apis.ts` 执行后删除）：`== FAIL 0`，`legacy read APIs checked: 102`。



## 补齐批次 D：智能体可控中心与人事行政

审计范围：`src/views/gap-d/BatchDPage.vue`、`src/pages/agent/**`、`src/pages/hr/**`、`src/pages/office/**`，以及批次 D 的类型、API 和 mock 服务。

| 页面区块 | 复用组件 | 处理与理由 |
| --- | --- | --- |
| 智能体、员工、行政列表 | `components/biz/ListPage`、`StatusChip`、`MoneyText` | 直接复用统一筛选、分页、状态和金额展示；服务层先裁剪工资字段。 |
| AI 总开关、工资批次、资产详情 | `components/biz/DetailPage`、Vuetify `VCard`/`VAlert`/`VTable` | `DetailPage` 提供 Vuexy 详情双栏和时间线；状态/明细是业务专属字段，表格使用 Vuetify 原生组件。 |
| 新工具、请假、规则维护 | `components/biz/FormPage`、`AppTextField`、`AppTextarea`、`VSwitch` | 复用现有表单页保存/取消和校验外壳；工具密钥只显示“已配置”。 |
| 可信度指标 | `components/KpiCard` | 复用现有 Vuexy `CardStatisticsHorizontal` 薄封装，没有新增卡片组件。 |
| AI 辅助区 | 顶部 `VAlert`；全局 `AssistantDrawer` | 仅在 AI 开启时显示 AI 状态提示，关闭时隐藏 AI 区；页面没有新造聊天或建议卡。 |

本批没有新增通用 UI 组件。`BatchDPage` 是批次专用页面编排器，原因是 26 个页面共享同一套静态 API、权限提示、工资字段裁剪和人工流程状态；路由文件保持薄壳，避免复制列表/详情/表单结构。Vuexy 对照采用 `apps/permissions`、`apps/user/view`、`apps/invoice/list` 和 `forms/form-wizard` 的布局语义，未复制其源码。

## 补齐批次 D 独立复用审计

审计基线：`git diff 3f325c0 --stat` 列出的本批 43 个 `frontend` 文件。逐页对照项目 `src/components/biz/*`、Vuexy full-version 的 `src/@core/components`、`src/components/dialogs`、`src/views/**`、`src/pages/**` 与 Vuetify 3.10。薪资/员工字段仍由 `src/mocks/services/gap-d.ts` 在接口层按有效权限裁剪，本审计没有改动该过滤。

| 组件/UI 块 | 位置 | 现成等价物 | 处理 | 原因 | 业务操作是否满足 |
| --- | --- | --- | --- | --- | --- |
| 批次 D 通用编排器 | `src/views/gap-d/BatchDPage.vue` | `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer` | 保留为薄组合并补齐抽屉 | 26 个路由只保留参数和 API 边界；页面分支只组合现成壳，不复制筛选/分页/详情/表单外框。 | 各分支有对应列表、详情或表单入口；写操作保留人工路径。 |
| 批次 D 路由薄壳 | `src/pages/agent/**`、`src/pages/hr/**`、`src/pages/office/**` | Vuexy 文件路由页面模式 | 保留 | 仅传入 `page-id`，没有重复 UI；路由、权限点和 `data-test` 不变。 | 满足路由进入与页面级权限守卫。 |
| 智能体/员工/行政列表 | `BatchDPage.vue` 的 G18/G20/G21/G22/G23/G26、HR01/02/04/05/12、AM01/02/05 | 项目 `ListPage`（内部 `VDataTableServer`、`TablePagination`） | 已替换/保留 | 所有列表统一筛选、分页、列设置、CSV；状态和金额继续用 `StatusChip`/`MoneyText`。 | 列表可筛选、分页、导出；可打开记录抽屉或进入详情。 |
| 可信度指标卡 | `BatchDPage.vue` 的 G22 | 项目 `KpiCard`；Vuexy `CardStatisticsHorizontal` | 已替换 | 补上采纳率、基线、降级次数三项指标，避免只展示一行静态文本。 | 满足指标查看与记录追溯；指标为演示数据。 |
| AI 总开关动作 | `BatchDPage.vue` 的 G19 | `DetailPage`、Vuetify `VCard/VAlert/VBtn`、`PermissionGate` | 保留并加权限门 | 状态切换是业务专属动作；按钮由现有角色动作权限控制，切换仍写审计。 | 正常/降级/关闭可用；AI 关闭后人工路径仍显示。 |
| 自治等级编辑 | `BatchDPage.vue` 的 G18 | `ListPage`、`StatusChip`、Vuetify `VSelect` | 保留并加权限门 | 每行等级和硬上限是业务字段，列表外壳交给 `ListPage`，硬上限仍由服务层校验。 | 可逐行保存；凭证/付款/薪资 L3 仍被硬上限拦截。 |
| 工具新增、配置与 MCP 导入 | `BatchDPage.vue` 的 G24/G25/G26 | `FormPage`、`RecordDrawer`、`PermissionGate`；Vuexy `AddNewUserDrawer` 模式 | 保留/补权限门 | 工具参数、只读标志、密钥“已配置”提示是业务内容，抽屉和表单外壳复用现成组件。 | 可新增默认停用只读工具、启停工具、导入 MCP；密钥不显示明文。 |
| 票据收件 | `BatchDPage.vue` 的 G20 | Vuetify `VFileInput`；Vuexy `forms/file-input.vue` | 保留 | 文件类型与收件动作需要业务 API，`VFileInput` 已是直接等价物。 | 可上传并进入待识别列表；AI 关闭时仍可人工收件。 |
| 薪资批次发起 | `BatchDPage.vue` 的 HR07 | `ListPage`、`MoneyText`、`StatusChip`、`PermissionGate` | 保留并加权限门 | 期间选择和确定性算薪是业务字段，列表与状态交给共享组件。 | 可按月发起算薪并进入复核；权限仍由服务层再次校验。 |
| 薪资明细表 | `BatchDPage.vue` 的 HR08/HR09 | 项目 `ListPage` + `RecordDrawer`；Vuexy invoice list/detail | 已替换 | 删除页面手写 `VTable`，统一分页/筛选；点员工打开抽屉查看规则版本和每个计算数字。 | HR08 满足逐人明细与规则查看；HR09 另有复核原因抽屉并提交审批。 |
| 薪资字段与工资条 | `BatchDPage.vue` 的 HR02/HR08/HR09/HR12 | `MoneyText`、`PermissionGate`；服务层字段裁剪 | 保留 | 金额只展示服务层提供的字段；无权字段继续显示“无权查看”或空列表。 | 员工/财务/人事范围由 07cd6ba 的接口过滤决定，未弱化。 |
| 社保/个税规则维护 | `BatchDPage.vue` 的 HR10 | `ListPage`、`FormDrawer`、`AppTextField`、`StatusChip` | 已替换 | 列表保留核实状态，新增/编辑改用共享表单抽屉，避免空泛展示页。 | 可新增/编辑版本；保存后标记待核实，不直接宣称合规。 |
| 请假、专项扣除、公告表单 | `BatchDPage.vue` 的 HR06/HR11/AM04 | `FormPage`、`AppTextField`、`AppTextarea` | 保留并补字段 | 全页表单适合这些路由；字段绑定草稿，保存后进入人工审批提示。 | 有标题/说明人工提交路径；具体后端接口接入前为演示草稿。 |
| HR03/AM03 详情 | `BatchDPage.vue` 的 HR03/AM03 | `DetailPage`、`RecordDrawer`、Vuexy user/order detail | 保留并补记录抽屉 | 详情双栏和时间线由 `DetailPage`，列表记录由 `RecordDrawer`；合同/资产等字段保持业务专属。 | 可查看详情与时间线；编辑/领用归还待后端接口接入。 |
| 通用记录详情与新增人工记录 | `BatchDPage.vue` 的 HR01/04/05、G21/23、AM01/02/05 | `RecordDrawer`、`FormDrawer`、`PermissionGate` | 已替换 | 原通用页只有展示；现在可打开记录详情，允许有权限用户新增人工待处理记录。 | 满足查看、人工登记和 AI 关闭时继续处理；状态流转待后端接口。 |
| 状态、金额、权限、AI 辅助区 | `BatchDPage.vue` 全部页面 | `StatusChip`、`MoneyText`、`PermissionGate`、全局 `AssistantDrawer` | 保留 | 这些组件承载项目状态字典、金额格式、五角色权限和只读助手语义，Vuexy/CASL 没有直接等价物；没有另造 `AgentCard`。 | 状态/金额/权限边界保持；AI 关闭时页面人工路径不依赖助手。 |

### 逐页操作复核

| 页面 | 复用 | 操作结论 |
| --- | --- | --- |
| G18/G19 | `ListPage`/`DetailPage` + `PermissionGate` | 自治等级保存、AI 三态切换满足；均保留审计提示。 |
| G20/G21/G22/G23 | `ListPage`、`KpiCard`、`RecordDrawer`、`FormDrawer` | 收件、提醒记录查看、可信度指标、范围登记满足；指标/范围数据为演示 mock。 |
| G24/G25/G26 | `DetailPage`、`FormPage`、`RecordDrawer`、`PermissionGate` | 工具启停、新增、MCP 导入满足；角色/参数高级配置待 API。 |
| HR01–HR06 | `ListPage`/`RecordDrawer`/`FormPage`/`FormDrawer` | 组织、员工、入离职、考勤查看与人工登记满足；审批/导入接口待接入。 |
| HR07–HR09 | `ListPage`、`DetailPage`、`RecordDrawer`、`FormDrawer`、`MoneyText` | 算薪、逐人明细、规则展开、复核原因和提交审批满足；金额继续由确定性 mock 服务提供。 |
| HR10–HR12 | `ListPage`、`FormDrawer`、`FormPage`、`MoneyText` | 规则版本新增/编辑、扣除草稿、本人工资条满足；薪资/员工可见范围由接口裁剪。 |
| AM01–AM05 | `ListPage`/`DetailPage`/`RecordDrawer`/`FormPage` | 合同、资产、公告、用品可查看并登记人工记录；领用归还、折旧、发布状态待 API。 |

本轮没有改动 `types/foundation.ts`、`utils/permission-engine.ts`、`stores/permissions.ts`，没有删测试，也没有修改后端或其他工作树。

## 批次 D 最新补齐记录

继续复用 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`MoneyText`、`StatusChip` 与 Vuetify 组件；新增操作通过既有页面壳组合，服务层负责权限、稳定主体、状态机、幂等与审计，AI 关闭时保留完整人工路径。


## 补齐批次 E


本批没有新增业务基础组件；12 个业务路由（K01–K09、HR13、ON01–ON02）都只是路由薄包装，实际由 `views/knowledge/KnowledgePage.vue` 按 `mode` 组合现有业务组件。逐页核对如下：

| 组件/UI 块 | 位置 | 现成等价物 | 处理 | 原因 | 业务操作是否满足 |
|---|---|---|---|---|---|
| 通用知识库页 | `src/views/knowledge/KnowledgePage.vue` | `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer` | 保留并改为薄组合 | 一个视图只负责数据加载、动作和插槽组合，表格、详情、表单、抽屉均由 biz 组件承载 | 满足列表筛选/分页、详情、新建/编辑、审批、人工路径、AI 开关和审计入口 |
| K01 空间列表与统计 | `src/pages/kb/index.vue`（`mode=home`） | Vuexy `front-pages/help-center/index.vue`、`apps/academy/my-course.vue`；项目 `ListPage`、`KpiCard` | 替换手写表格为 `ListPage`，统计保留 `KpiCard` | 空间行需要统一列设置、关键词筛选、分页和 CSV | 满足空间打开、全文搜索、新建入口；最近更新和收藏没有独立数据源，当前以空间列表/关键词检索承载，已记录为范围限制 |
| K01 搜索结果 | `KnowledgePage.vue` 的全文搜索块 | Vuetify `VList`（Vuexy help-center 搜索结果模式） | 保留 `VList` | 每行需要同时展示空间、版本、摘要和点击出处，非通用数据表格 | 满足检索、打开文档、AI 关闭时仍可人工检索 |
| K02 文档详情与版本 | `mode=doc` | 项目 `DetailPage` 时间线、`ListPage`、`RecordDrawer`；Vuexy `front-pages/help-center/article/[title].vue`、`TiptapEditor.vue` | 修正状态绑定，版本表改为 `ListPage`，版本正文用 `RecordDrawer` | 版本可筛选、分页、查看正文，详情右栏复用 `DetailPage` 时间线 | 满足阅读、版本历史、编辑/提交审核、标签/有效期、审计时间线；附件采用元数据 mock 登记，页面明确不伪造真实文件 |
| K03 空间权限与文档 | `mode=space` | 项目 `DetailPage`、`ListPage`、`FormDrawer`；Vuexy `apps/academy/my-course.vue`、`apps/ecommerce/product/category-list.vue` | 文档 `VList` 改为 `ListPage`，权限开关改为 `FormDrawer` | 权限变更需要显式保存和审计，文档列表需要筛选/列设置 | 满足空间文档列表、打开详情、仅财务开关和审计；成员/文件夹采用 mock 可保存编辑，并通过可见角色过滤文档与检索 |
| K04 编辑与发布 | `mode=edit` | 项目 `FormPage`；Vuexy `forms/editors.vue`、`TiptapEditor.vue` | 保留 `FormPage`，正文改用 `@core/components/TiptapEditor.vue` | 避免重复实现富文本工具栏，保存仍只产生草稿 | 满足新建、编辑、保存草稿、提交审核和人工发布检查；AI 关闭时表单仍可用 |
| K05 发布审核 | `mode=review` | 项目 `ListPage`、`StatusChip`、`FormDrawer`；Vuexy `tables/data-table.vue`、`components/dialogs/ConfirmDialog.vue` | 保留说明卡片，审批/驳回改为 `PermissionGate` + `FormDrawer` 显式提交 | 驳回原因和批准动作必须在明确的提交抽屉中完成并写审计 | 满足队列筛选、批准、驳回、原因记录、发布审计 |
| K06 问答沉淀 | `mode=qa` | 项目 `ListPage`、`RecordDrawer`、`PermissionGate`；Vuexy `pages/faq.vue` | 列表统一 `ListPage`，问答正文和出处用 `RecordDrawer` | 行内摘要不足以查看完整答案和引用 | 满足已发布问答查看、出处跳转、生成建议；建议动作受权限控制，AI 关闭时仍可查看和人工沉淀 |
| K07 到期提醒 | `mode=expiring` | 项目 `ListPage`；Vuexy `tables/data-table.vue`、`pages/components/chip.vue` | 保留 `ListPage`，状态使用 Vuetify `VChip` | `upcoming/expired` 尚未进入项目 `StatusChip` 字典，避免伪造状态含义 | 满足到期清单筛选、状态和文档详情跳转；消息中心推送由 mock 服务幂等登记，真实渠道仍待后端接入 |
| K08 检索与索引 | `mode=index` | 项目 `DetailPage`、`ListPage`、`PermissionGate`；Vuexy `pages/components/progress-linear.vue`、`tables/data-table.vue` | 检索结果 `VList` 改为嵌入式 `ListPage`，重建按钮加权限门 | 结果需要统一分页/列设置，重建是写动作 | 满足索引状态、重建、检索测试、引用文档；重建和检索均可在 AI 关闭时人工执行并写审计 |
| K09 敏感访问日志 | `mode=access` | 项目 `ListPage`、`RecordDrawer`；Vuexy `tables/data-table.vue` | 增加来源筛选和访问详情抽屉 | 日志需要按人工/AI 过滤并查看完整字段 | 满足查看、筛选、详情和下载/AI 访问审计记录 |
| HR13 个人档案 | `mode=employee` | 项目 `DetailPage`、`ListPage`、`RecordDrawer`、`PermissionGate`；Vuexy `views/apps/user/view/UserTabAccount.vue` | 文件 `VList` 改为 `ListPage`，详情/下载改用 `RecordDrawer` + 权限门 | 下载动作不能只靠展示列表，必须明确写访问审计 | 满足按权限查看、详情、下载和审计；上传登记接口已在本批 mock 数据中心提供，明确标注模拟存储 |
| ON01 新人上手 | `mode=onboarding` | 项目 `DetailPage`、全局 `AssistantDrawer`；Vuexy `apps/academy/course-details.vue`、`pages/extensions/tour.vue` | 保留清单 `VList`，增加 `VProgressLinear`；AI 区继续由全局助手和本页引用问答承载 | 清单是可勾选任务而非通用数据表，进度条复用 Vuetify | 满足按角色清单、勾选保存、带我去做、带出处问答；AI 关闭时清单和页面跳转仍可用 |
| ON02 清单配置 | `mode=onboarding-admin` | 项目 `ListPage`、`FormDrawer`；Vuexy `apps/kanban/index.vue`、`pages/extensions/tour.vue` | 移除行内失焦保存，改为点击行打开 `FormDrawer` 后显式保存 | 防止每次失焦产生不可见写入，统一表单校验/保存体验 | 满足清单筛选、编辑任务/说明/引导地址、保存审计；分步 tour 配置以角色模板和页面地址 mock 保存，真实引导引擎待后端接入 |
| AI 交互与 AgentCard | `src/App.vue`、`src/components/biz/AssistantDrawer.vue` | 项目现有 `AssistantDrawer`、`ChatLog`、`ChatMessageForm`；AgentCard 渲染在助手内部 | 复用，不在知识库页新造卡片 | 批次 E 只需要带出处建议，助手已处理 AI 状态开关 | AI 关闭时助手和页面 AI 区隐藏，人工路径保留；没有金额或 AgentCard 专属业务块 |
| 金额展示 | 批次 E 全部页面 | 项目 `MoneyText` | 不引入 | 知识库、档案、上手清单没有金额字段，使用 `MoneyText` 会制造无意义语义 | 不适用 |

仍未接入的范围限制是：真实文件存储、外部通知渠道、向量索引和生产级 tour 引擎；本批 API/mock 已提供元数据登记、权限保存、通知写入和审计记录。



## 补齐批次 E 缺口复核（2026-11-10）

复核后仍沿用 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`StatusChip`、`PermissionGate` 和 Vuetify `VList/VTreeview` 语义组合，没有新增通用业务组件。附件/档案上传复用原生文件 input + `FormDrawer`/详情抽屉；空间文件夹和成员区是空间专属编辑区，因需要同时展示树、角色范围和成员明细而保留在 `KnowledgePage`，数据操作全部经 `src/api/gap-e.ts`。消息中心复用 `ListPage`，管理员通知开关仍使用 Vuetify `VSwitch`。本轮已把此前「未补齐」的附件、成员/文件夹、通知推送、上手模板配置改为可保存、可校验、可追溯的 mock；真实存储和外部渠道仍明确标注为模拟。


## 补齐批次 E 增量复用审计（第二轮）

审计日期：2026-11-10
审计范围：`b1cd3c3..137ec75` 的新增或改动文件，重点检查 `src/views/knowledge/KnowledgePage.vue`、`src/pages/agent/knowledge/[id].vue`、`src/plugins/1.router/index.ts`、`src/api/gap-e.ts`、`src/mocks/services/gap-e.ts`、`src/api/mock-client.ts` 及相关类型。

### 复用结论

- `KnowledgePage.vue` 继续组合 `ListPage`、`DetailPage`、`FormPage`、`FormDrawer`、`RecordDrawer`、`StatusChip`、`PermissionGate` 和 `@core/components/TiptapEditor.vue`。本轮没有新增页面级通用组件，也没有把列表、详情、表单、抽屉或状态标签重新实现一遍。
- `pages/agent/knowledge/[id].vue` 仍是旧路由薄包装；`plugins/1.router/index.ts` 只调整静态 `/kb/index` 路由的匹配顺序。两处没有重复业务 UI。
- 页面写操作仍经 `src/api/gap-e.ts`，展示金额在本增量中没有新增或改写；因此没有发现需要替换为 `MoneyText` 或 `utils/money` 的金额块。

### 权限、身份、幂等与审计核对

- **[通过] 有效权限：** API 层调用 `assertCan`，服务层对创建、更新、审核、建议、归档、附件、员工档案、空间成员和文件夹等写操作再次执行 `can`/管理员校验；读取路径按空间可见范围过滤。
- **[通过] 稳定身份与防自审：** `currentActor()` 使用会话的 `session.userId`，审核记录保存 `submittedBy`，服务层按稳定身份比较提交人与审核人，显示名不参与自审判断。
- **[通过] 防重复审核和重复提交：** 审核只接受 `pending`，文档只接受 `draft` 且不存在待审记录；独立接口验收覆盖了越权、仅财务空间隔离、不存在 ID、自审和重复审核。
- **[通过] 稳定审计身份：** `writeAudit()` 持久化 `Actor.id` 为 `actorId`，文档、审核、空间权限、附件、员工档案等写审计均沿用会话身份；哈希链也覆盖该字段。
- **[通过] 附件读回身份：** `uploadKbAttachment()` 复用同一个原始 `Actor` 完成上传后的读回，敏感文档访问审计保留真实角色和身份。
- **[通过] 审核原子更新：** `decideReview()` 在任何状态写入前校验审核记录、提交人、目标文档/问答及文档状态，校验失败时保持原审核记录不变。
- **[通过] 关闭「仅财务」：** `setSpaceFinanceOnly(false)` 同步清除 `visibleRoles`，空间提示、空间文档列表和检索范围重新对所有已授权角色一致开放。
- **[建议修改] 部分写接口没有请求级幂等键或重复提交保护：** 创建文档、创建版本、生成建议问答、创建文件夹、上传附件和上传员工档案在网络重试时会追加重复记录；审核和提交文档已有状态保护。后续接入真实 API 时应补充幂等键或业务去重约束。

本轮闭环修复以上四项阻断，并在 `verify-gap-e-writes.ts` 增加对应回归断言；旧 `/agent/knowledge` 入口继续通过薄包装迁移到新知识库，未知详情 ID 显示明确空态。真实文件存储、外部通知和生产级索引仍属于原有范围限制。
