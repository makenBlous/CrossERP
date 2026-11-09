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
