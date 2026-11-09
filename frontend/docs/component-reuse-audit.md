# 组件复用审计

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
