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


