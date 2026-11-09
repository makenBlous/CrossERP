# 第 2 批组件复用检查

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

## 汇总

- 审计条目：32 个（按可独立替换的页面块计数；同一共享列表在多个页面按页面族合并记录）。
- 已替换：4 个页面块，涉及 2 个文件：利润页店铺表金额列、SKU 表金额列、结算详情总额、结算详情明细金额。
- 保留：28 个页面块。保留原因集中为：已经使用项目共享封装；Vuetify 原生组件就是 Vuexy 对应实现；或业务交互（文件类型、双动作审批抽屉、核销双栏）没有安全的一对一替代。
- 共享文件编辑：无。组件替换只修改了范围内的两个页面文件并新增本审计文档；列表路由文件名调整由独立的批次路由修复提交完成。
