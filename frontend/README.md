# CrossERP 前端静态原型

这是 CrossERP 的浏览器静态原型。页面使用假数据，不连接后端。这一阶段打好地基：共享业务组件、统一假数据中心、全局智能助手。以后只把假数据层换成 `/api/v1`，把智能助手换成 DeerFlow，页面本身不改。

Vuexy 是商业模板。定制后的 `frontend/` 不要放进公开仓库，除非许可证允许。详见仓库 `docs/design/00-总览.md`。

## 环境要求

- Node.js 20 或以上
- pnpm（本目录已有 `pnpm-lock.yaml`，不要改用 npm 或 yarn）

## 启动

在 `frontend/` 目录执行：

```bash
pnpm install
pnpm dev
```

浏览器打开终端里打印的本地地址。默认语言是简体中文，顶栏可以切换 English，也可以切换明暗主题。

生产构建：

```bash
pnpm build
```

类型检查：

```bash
pnpm run typecheck
```

## 登录和角色

登录页任意输入即可进入。密码不会写入存储。

顶栏角色切换器有五种角色：管理员、运营、财务、只读、审计。切换后左侧菜单按 `src/config/pages.ts` 里的可见角色过滤。直接打开无权限地址会进入 `/not-authorized`。

按钮是否显示，用 `PermissionGate` 或指令 `v-can`。规则在 `src/utils/permission.ts` 的 `can(role, action)`：

| 角色 | 允许的动作 |
|---|---|
| 管理员 | 查看、新建、修改、删除、审批、导出、发货、收货、提交建议 |
| 运营 | 查看、新建、修改、导出、发货、收货、提交建议 |
| 财务 | 查看、审批、导出、提交建议 |
| 只读 | 查看 |
| 审计 | 查看、导出 |

禁用而不是隐藏：`v-can.disable="'approve'"`。

## 目录

- `src/config/pages.ts`：全部页面配置。菜单和占位页都从这里生成。菜单项的 `to` 必须是 `{ path }`，不要写成字符串。
- `src/config/status.ts`：单据状态字典。每种状态有值、中文名、英文名、颜色。
- `src/components/biz/`：共享业务组件。
- `src/types/entities.ts`：假数据中心的实体类型，对照 `docs/design/04-数据模型.md`。
- `src/mocks/seed/`：固定种子数据。
- `src/mocks/services/`：业务流转。金额在这里按规则计算。
- `src/stores/mockdb.ts`：内存数据，并写入 `localStorage`。
- `src/api/`：页面只调用这里的函数。
- `src/agent/`：智能助手适配器。现在是 `MockAgentAdapter`。
- `src/pages/`：已经做成静态页的路由。没有单独 `.vue` 文件的地址由占位页渲染。
- `src/plugins/i18n/`：中文和英文文案。

## 怎么加一个页面

1. 在 `src/config/pages.ts` 增加一条记录：路径、中英文名称、分组、图标、可见角色、目的、主要区块、阶段。
2. 若要出现在左侧菜单，把 `showInMenu` 设为 `true`，并指定 `group`。`to` 使用 `{ path: '/你的路径' }`。
3. 还没做界面时不用新建 `.vue`。路由会指向占位页，显示名称、目的、计划区块和阶段。
4. 要做成真实静态页时，先在 Vuexy full-version 里找对应页面（列表、详情、抽屉、向导、日历、聊天），再在 `src/pages/` 按路径建文件，并把该条的 `implemented` 设为 `true`。列表页用 `ListPage`，详情页用 `DetailPage`，抽屉用 `FormDrawer`。
5. 中英文菜单名来自配置。页面里的句子写进 `src/plugins/i18n/ui.ts` 的两种语言。
6. 页面只调用 `src/api/`，不直接改 `src/mocks/`。

## 地基组件

组件都在 `src/components/biz/`，文案走 i18n。

### ListPage

标题、筛选、已保存视图、列设置、批量操作、分页、导出 CSV。筛选和列设置保存在本机 `localStorage`，键名带 `storage-key`。导出的是当前筛选结果，不是当前页。CSV 由浏览器生成。

```vue
<ListPage
  storage-key="orders"
  :title="t('orders.title')"
  :items="orders"
  :columns="columns"
  :filters="filters"
  date-key="orderedAt"
  :loading="loading"
  :error="error"
  :batch-actions="[{ key: 'export', label: '导出选中' }]"
  @retry="load"
  @batch="onBatch"
>
  <template #item.status="{ item }">
    <StatusChip domain="sales_order" :value="item.statusCode" />
  </template>
</ListPage>
```

`columns` 形如 `{ key, title, align? }`。下拉筛选比较该列的文本。日期筛选要求该字段能取出 `YYYY-MM-DD`。

### DetailPage

头部放标题、`StatusChip` 和 `#actions`。左侧是默认插槽（放标签页或正文）。右侧是审计轨迹和关联单据。

```vue
<DetailPage
  title="PO-2026-001"
  domain="purchase_order"
  status="approved"
  :timeline="events"
  :related="docs"
>
  <template #actions>
    <VBtn>收货</VBtn>
  </template>
  <VTabs>...</VTabs>
</DetailPage>
```

### FormDrawer / FormPage

抽屉改编自 Vuexy `AddNewUserDrawer`（`AppDrawerHeaderSection` + `PerfectScrollbar` + `VForm`）。整页表单改编自 ecommerce product add。保存前走 Vuetify 校验。规则在 `@core/utils/validators`：`requiredValidator`，以及带中文提示的 `requiredText`、`numberText`、`moneyText`。`@save` 里调用 `src/api/`，不要在组件里写业务。

```vue
<FormDrawer v-model="open" title="新建采购单" :saving="saving" @save="save">
  <AppTextField v-model="form.amount" :rules="[requiredText('请填写金额'), moneyText('金额最多 4 位小数')]" />
</FormDrawer>
```

### StatusChip、MoneyText、状态页

`StatusChip` 按 `domain` + `value` 取 `src/config/status.ts`。`MoneyText` 只格式化。折算金额由调用方传入 `converted`，组件不猜汇率。

`EmptyState` 用 `VEmptyState`，`LoadingState` 用 `VSkeletonLoader`，`ErrorState` 用 `VAlert`。`useConfirm()` 弹出 Vuexy `ConfirmDialog`（由 `ConfirmHost` 接入），返回 `Promise<boolean>`。

## 假数据中心

实体类型在 `src/types/entities.ts`。金额在服务层用万分位整数（`src/utils/money.ts`），不用 `float` 做加减。展示时再四舍五入。

种子由 `buildSeed()` 生成，随机序列固定为 `20261109`，每次重置都一样。同一批店铺、SKU、供应商、仓库、客户贯穿各域。

大约规模：

| 对象 | 数量 |
|---|---|
| 公司 | 1 |
| 店铺 | 6（Amazon US / UK / DE / JP、Shopify、TikTok Shop） |
| SKU | 40 |
| 供应商 | 10 |
| 仓库 | 8（FBA、海外仓、国内仓） |
| 订单 | 100 |
| 采购单 | 12 |
| 头程 | 6 |

Pinia 仓库 `useMockDbStore` 把整库放在内存，并写入 `localStorage` 键 `crosserp-mockdb-v1`。顶栏用户菜单里的「重置演示数据」会恢复种子并刷新页面。已保存的列表视图不在这次重置里。

## 流转规则

动作都在 `src/mocks/services/`，每个动作写审计轨迹：谁、何时、做了什么。页面通过 `src/api/workflows.ts` 调用。

1. 采购单：草稿 → 提交（生成待审批）→ 批准 → 收货。收货生成收货记录、入库单和库存流水，库存增加。未批准不能收货。
2. 头程：计划中 → 发运。始发仓可售减少，目的 FBA 在途增加。签收后在途转为可售，并生成入库单。
3. 订单发货：待发货 → 已发货。生成出库单，履约仓库存减少。库存不足会拒绝。
4. 订单利润：规则版本 `demo-rule-1`。只对已发货、部分退款、已退款的订单计算。
   - 收入 = 商品金额 − 分摊退款
   - 平台费：Amazon 15%，Shopify 3.4%，TikTok Shop 8%
   - 广告计提：收入的 5%（演示规则，不是广告账单）
   - 头程和成本：取 SKU 生效期成本，按演示月汇率折到订单币种
   - 利润 = 收入 − 平台费 − 广告 − 头程 − 成本
5. 智能体建议只创建待审批记录，不写账、不改金额。

采购退货、调拨单和盘点单在种子里是草稿，这一阶段不改库存。

## API 注释约定

页面只调用 `src/api/`。每个函数上方写未来的真实接口，例如：

```ts
// 未来: GET /api/v1/sales/orders
export async function fetchOrders() { ... }
```

函数返回 `Promise`，并模拟大约 160 ms 延迟。返回类型保持稳定。页面不要读 `src/mocks/`。

## 换成真实接口

1. 保持函数名和返回类型不变。
2. 把函数体里的 `useMockDbStore()` 换成对 `/api/v1/...` 的请求。注释里的路径就是对照。
3. 金额仍由服务端按确定性规则算好。页面只展示。
4. 写操作仍走审批。前端不要自己改利润或匹配结果。

## 换成 DeerFlow

适配器接口在 `src/agent/adapter.ts`：

```ts
sendMessage(context, message, emit) => Promise<void>
```

`context` 带页面名、路由和选中记录 id。`emit` 分段吐出文本或卡片。

现在 `src/agent/index.ts` 的 `createAgentAdapter()` 返回 `MockAgentAdapter`。换成 DeerFlow 时：

1. 新建 `DeerFlowAdapter`，实现同一个接口。请求发到本机 DeerFlow（设计文档里的默认地址是 `127.0.0.1:2026`），不要把密钥写进仓库。
2. 把 `createAgentAdapter()` 改成返回 `DeerFlowAdapter`。
3. 助手抽屉和页面不用改。
4. 适配器不计算金额。数字来自 CrossERP 只读结果。
5. 需要写业务时，只调用 `submitAgentSuggestion()`，生成待审批建议。

每个页面右下角都有助手按钮。它知道当前页面和路由参数里的记录 id。订单详情还会写入选中 id。

## 组件来源对照表

新页面先找 Vuexy 现成页面或组件，再考虑自写。只读参考在 `D:\make\write\vue\vuexy-10.11.1\vuexy-admin-v10.11.1\vue-version\typescript-version\full-version`。不要改那个目录。

完整的逐组件审计见 [`docs/component-reuse-audit.md`](docs/component-reuse-audit.md)。本表记录页面级复用关系；通用 UI 优先落到 Vuexy/Vuetify，业务组件只保留领域数据和权限适配。

| 已实现页面 | 改编自 |
|---|---|
| `/dashboard` | dashboards/ecommerce 的统计卡（`CardStatisticsHorizontal`）+ Apex 图表 |
| `/dashboard/todos` | `ListPage`（product list / user list） |
| `/dashboard/stores` | `ListPage` + 图表卡 |
| `/dashboard/calendar` | `pages/apps/calendar.vue`：左栏 `AppDateTimePicker`（inline）+ 类型筛选 + FullCalendar。不新建事件 |
| `/catalog/skus`、`/catalog/brands`、`/catalog/categories`、`/catalog/bundles`、`/catalog/costs`、`/catalog/mappings`、`/catalog/listings` | `ListPage` + `FormDrawer`（`AddNewUserDrawer`） |
| `/catalog/skus/:id`、`/catalog/listings/:id` | `DetailPage`（order details 左右栏 + `VTimeline`）+ `FormDrawer` |
| `/orders`、`/orders/exceptions`、`/orders/fulfillment`、`/orders/returns`、`/orders/channels` | `ListPage`；渠道页顶部统计卡用 `CardStatisticsHorizontal` |
| `/orders/:id` | order details 头部与时间线；页内 `VTabs` 用 user view 的 `v-tabs-pill` |
| `/inventory/on-hand` | user list 统计卡 + `ListPage` |
| `/inventory/warehouses`、`/inventory/movements`、`/inventory/alerts` | `ListPage` + `FormDrawer`（仓库档案） |
| `/inventory/fba`、`/inventory/overseas`、`/inventory/domestic` | logistics/dashboard 的数字卡 + `ListPage`。同步按钮未做，因为原型没有平台拉数 |
| `/inventory/inbound`、`/inventory/outbound`、`/inventory/transfers`、`/inventory/counts` | invoice list + 明细行编辑；详情用审批页同款抽屉。盘点过账自写差异计算，Vuexy 没有盘盈盘亏 |
| `/procurement/suppliers` | ecommerce customer list / `ListPage` + `FormDrawer` |
| `/procurement/suppliers/:id` | user view：`DetailPage` + `v-tabs-pill` |
| `/procurement/orders`、`/procurement/receipts`、`/procurement/returns`、`/procurement/statements` | invoice list / `ListPage` |
| `/procurement/orders/new` | `AppStepper` + form-wizard-numbered。保存/提交按钮放在页头，三步都能填 |
| `/procurement/orders/:id` | invoice preview：`DetailPage` 头、行、收货、附件空态 |
| `/logistics/first-mile`、`/logistics/carriers`、`/logistics/rate-cards`、`/logistics/tracking`、`/logistics/fee-check` | logistics dashboard 的列表形态 + `ListPage`。轨迹页不放地图：种子没有坐标 |
| `/logistics/shipments/:id` | fleet/invoice preview：`DetailPage` 路线、货箱、费用、轨迹 |
| `/finance/recon`、`/finance/issues`、`/finance/vouchers` | `ListPage`；对账页顶部统计卡 |
| `/finance/profit` | dashboards 柱状图 + 嵌入式 `ListPage` |
| `/finance/imports`、`/finance/settlements`、`/finance/accounts`、`/finance/fx-rates`、`/finance/fee-map`、`/finance/column-maps`、`/finance/ar`、`/finance/ap`、`/finance/clearing`、`/finance/exports`、`/finance/cash` | invoice list / user list 的 `ListPage` 薄封装 + `KpiCard`/`VDataTable` |
| `/finance/imports/:id`、`/finance/rows/:table/:id`、`/finance/settlements/:id`、`/finance/recon/:id`、`/finance/issues/:id`、`/finance/profit/sku/:internalSku`、`/finance/vouchers/:id` | invoice preview + order details 的 `DetailPage` + `VTimeline` |
| `/ads/campaigns`、`/ads/performance` | dashboards/analytics 图表卡 + `ListPage` |
| `/ads/imports` | forms/file-input 的 `VFileInput` + `ListPage` |
| `/ads/allocations` | form-validation 表单 + 结果 `ListPage` |
| `/approvals` | `ListPage`；右侧抽屉用 `AppDrawerHeaderSection` + `PerfectScrollbar`（同 AddNewUserDrawer 外壳，不是表单） |
| `/approvals/submitted`、`/approvals/:id` | invoice preview 的详情卡 + `DetailPage` 时间线 |
| `/approvals/workflows` | form-wizard-icons 的步骤结构（用 `VExpansionPanels` 呈现静态步骤） |
| `/crm/accounts` | user list / `ListPage` |
| `/crm/accounts/:id` | user view：`DetailPage` + `v-tabs-pill` + `VWindow` |
| `/agent/chat` | `pages/apps/chat.vue` + `views/apps/chat/ChatLog.vue` + 消息输入条 |
| `/agent/definitions` | roles 卡片：`VCard` + `VAvatar` + `VChip` |
| `/agent/runs` | `ListPage` |
| 全局智能助手抽屉 | chat 气泡和输入条，套在 `VNavigationDrawer` 里 |
| `/crm/*`、`/admin/*`、`/account/*` | 第 3 批列表统一改编自 `/pages/apps/user/list` / `/views/apps/roles`，详情改编自 `/pages/apps/user/view`，表单改编自 `/pages/pages/account-settings` |
| `/crm/leads/board`、`/crm/opportunities` | Vuexy `/pages/apps/kanban/index.vue` + `/views/apps/kanban/KanbanItems.vue`（FormKit 拖拽） |
| `/agent/*` | 列表 `ListPage`，详情 `DetailPage` + `v-tabs-pill`/`VWindow` + `VTimeline`，DeerFlow 使用 Vuexy wizard `VStepper` |
| `/audit`、`/security-log`、`/audit/verify`、`/audit/export` | `、`/`、` |

| 复用规则 | 当前实现 |
|---|---|
| 列表、筛选、分页、列设置、批量操作 | `ListPage`（内部复用 `VDataTableServer`、`TablePagination` 和 Vuexy App form elements） |
| 详情、审计轨迹、关联单据 | `DetailPage`（Vuexy order/invoice detail + Vuetify `VTimeline`） |
| 表单抽屉和只读记录抽屉 | `FormDrawer` / `RecordDrawer`（Vuexy `AddNewUserDrawer`、`AppDrawerHeaderSection`、`PerfectScrollbar`） |
| 统计卡 | `KpiCard` → Vuexy `CardStatisticsHorizontal` |
| 步骤导航 | Vuexy `AppStepper`；采购新建页不再手写步骤条 |
| 状态、金额、权限、智能助手 | `StatusChip`、`MoneyText`、`PermissionGate`、`AgentAdapter`，因业务语义无模板等价物而保留薄封装 |

`ListPage` 是 product list / user list / invoice list 的薄封装：可选统计卡插槽、筛选 `VCard`、`AppTextField` / `AppSelect` / `AppDateTimePicker`、`VDataTableServer`、`TablePagination`、批量操作。店铺筛选（`store` / `storeId` / `storeName`，或 `store: true`）的「全部」是「全部店铺」，其他筛选是「全部」。

校验用 `@core/utils/validators`。`requiredText` / `numberText` / `moneyText` 只替换提示文案，判断仍走 `requiredValidator` / `decimalValidator` / `moneyValidator`。full-version 没有小数和金额校验，后两个按 `integerValidator` 的写法补在同一文件。

### 仍自写的组件

| 组件 | 原因 |
|---|---|
| `StatusChip` | Vuexy 的 `VChip` 没有本项目状态字典和中英文名 |
| `MoneyText` | 没有币种 + 折算额展示组件，且不计算金额 |
| `PermissionGate` / `can` | Vuexy CASL 不是这五种角色 |
| `AgentAdapter` | chat 只渲染消息，没有只读查询和待审批建议 |
| `ListPage` / `DetailPage` / `FormDrawer` / `FormPage` | 薄封装，业务数据仍由页面传入 |
| `KpiCard` | 只把 `value` 映射到 `CardStatisticsHorizontal`，并补一行 hint |
| `EmptyState` / `LoadingState` | 分别包 `VEmptyState` / `VSkeletonLoader`，文案走 i18n |
| `ConfirmHost` | 把 `useConfirm()` 接到 Vuexy `ConfirmDialog` |
| `views/apps/chat/ChatLog.vue`、`ChatMessageForm.vue` | 从 Vuexy chat 拆出，去掉演示 store，给助手抽屉和 `/agent/chat` 共用 |
| `pages/finance/_components/FinanceTablePage.vue` | 模块专用薄封装，统一 finance/ads/approval 表格的列、详情跳转和空状态 |
| `pages/finance/_components/FinanceDetail.vue` | 模块专用薄封装，复用 `DetailPage` 并统一金融详情页插槽 |
| `pages/finance/_components/FinanceUpload.vue` | 模块专用上传外壳，复用 Vuetify `VFileInput`；需要展示解析提示与导入状态 |

## 许可证提醒

界面骨架来自 Vuexy 商业后台模板。不要把 `frontend/`、模板源码或商业图片提交到公开仓库。本原型只供内部演示。

## 只看效果：用构建版

```bash
pnpm build
pnpm exec vite preview --host 127.0.0.1 --port 4173
```

浏览器打开 http://127.0.0.1:4173 。构建版不需要边打开边编译，首次打开不到 1 秒。`pnpm dev` 开发版第一次启动（或依赖变化后）需要预编译，首屏可能要十几秒，之后很快。`vite.config.ts` 里已预先打包常用依赖，避免首次访问时整页重载导致白屏。Vue DevTools 默认关闭，需要时用 `VITE_DEVTOOLS=1 pnpm dev`。


