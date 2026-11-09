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
