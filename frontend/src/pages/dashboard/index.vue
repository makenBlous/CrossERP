<script setup lang="ts">
import type { ApexOptions } from 'apexcharts'
import { fetchHome } from '@/api/home'
import { fetchMyDashboard, fetchPeriods } from '@/api/dashboard'
import type { HomePayload } from '@/api/home'
import type { DashboardPayload } from '@/types/domain'
import { canPermission } from '@/api/mock-client'
import { useOnboardingTour } from '@/components/tour/useOnboardingTour'
import { useChartTheme } from '@/composables/useChartTheme'
import { useAiModeStore } from '@/stores/ai-mode'
import { useSessionStore } from '@/stores/session'
import { formatInteger, formatMoney, formatPercent } from '@/utils/format'

const session = useSessionStore()
const aiMode = useAiModeStore()
const { isRunning, restart, start } = useOnboardingTour()
const chart = useChartTheme()

const loading = ref(true)
const home = ref<HomePayload | null>(null)
const error = ref('')
const reportData = ref<DashboardPayload | null>(null)
const reportPeriods = ref<string[]>([])
const reportPeriod = ref('2026-10')
const reportStoreId = ref('all')

const roleNames: Record<string, string> = {
  admin: '管理员',
  finance: '财务',
  employee: '普通员工',
  customer_service: '客服/售后',
  operator: '运营',
  viewer: '只读用户',
  auditor: '审计',
}

const roleName = computed(() => roleNames[session.role] ?? '团队成员')

const shortcuts = computed(() => [
  { title: '我的待办', detail: '查看当前需要处理的任务', icon: 'tabler-list-check', to: '/dashboard/todos', permission: 'report:read' },
  { title: '订单', detail: '查看权限范围内的订单', icon: 'tabler-receipt', to: '/orders', permission: 'sales_order:read' },
  { title: '经营日历', detail: '查看到货、打款和发货日期', icon: 'tabler-calendar-event', to: '/dashboard/calendar', permission: 'report:read' },
  { title: '审批中心', detail: '查看你有权限读取的审批', icon: 'tabler-checkbox', to: '/approvals', permission: 'approval:read' },
  { title: '我的数据范围', detail: '查看当前主体可读取的数据范围', icon: 'tabler-shield-check', to: '/me/data-scope', permission: 'user:read' },
].filter(item => canPermission(item.permission)))

const visibleTasks = computed(() => home.value?.tasks.slice(0, 6) ?? [])
const visibleApprovals = computed(() => home.value?.approvals.slice(0, 5) ?? [])

const reportReadable = computed(() => canPermission('report:read'))

const reportStoreItems = computed(() => [
  { title: '全部可见店铺', value: 'all' },
  ...(reportData.value?.stores ?? []).map(item => ({ title: `${item.storeName} · ${item.marketplace}`, value: item.storeId })),
])

const reportPeriodItems = computed(() => reportPeriods.value.map(item => ({ title: item, value: item })))

const trendOptions = computed<ApexOptions>(() => ({
  chart: { toolbar: { show: false }, parentHeightOffset: 0, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 3 },
  colors: [chart.primary.value, chart.success.value],
  dataLabels: { enabled: false },
  xaxis: { categories: reportData.value?.trend.map(item => item.month) ?? [], labels: { style: { colors: chart.label.value } } },
  yaxis: { labels: { style: { colors: chart.label.value } } },
  grid: { borderColor: chart.grid.value },
  legend: { labels: { colors: chart.label.value } },
  tooltip: { theme: chart.label.value.includes('225') ? 'dark' : 'light' },
}))

const trendSeries = computed(() => [
  { name: '销售额', data: reportData.value?.trend.map(item => item.sales) ?? [] },
  { name: '净利润', data: reportData.value?.trend.map(item => item.profit) ?? [] },
])

const reasonOptions = computed<ApexOptions>(() => ({
  labels: reportData.value?.reasons.map(item => item.code) ?? [],
  colors: [chart.error.value, chart.warning.value, chart.info.value, chart.primary.value],
  legend: { position: 'bottom', labels: { colors: chart.label.value } },
  dataLabels: { enabled: false },
  stroke: { width: 0 },
}))

const reasonSeries = computed(() => reportData.value?.reasons.map(item => item.count) ?? [])

const scopeLabels = computed(() => {
  const scopes = home.value?.scope?.dataScopes
  if (!scopes)
    return []

  const labels: string[] = []
  if (scopes.orders.length)
    labels.push(`订单：${scopes.orders.join('、')}`)
  if (scopes.expenses.length)
    labels.push(`费用：${scopes.expenses.join('、')}`)
  if (scopes.employees.length)
    labels.push(`员工：${scopes.employees.join('、')}`)

  return labels
})

const summaryCards = computed(() => {
  const data = home.value

  const cards = [
    { title: '待处理任务', value: formatInteger(data?.tasks.length ?? 0), hint: '来自当前角色可读的业务提醒', icon: 'tabler-bell-ringing', color: 'warning' },
    { title: '待审批事项', value: formatInteger(data?.approvals.length ?? 0), hint: '仅展示当前权限允许读取的审批', icon: 'tabler-checkbox', color: 'primary' },
    { title: '可读订单', value: formatInteger(data?.orders.length ?? 0), hint: '按当前主体数据范围过滤', icon: 'tabler-receipt', color: 'info' },
    { title: '可读费用', value: formatInteger(data?.expenses.length ?? 0), hint: '按当前主体数据范围过滤', icon: 'tabler-report-money', color: 'success' },
  ]

  if (data?.dashboard) {
    cards[2] = { title: '销售额摘要', value: formatMoney(data.dashboard.kpi.sales, 'USD'), hint: '来自已授权的经营报表', icon: 'tabler-chart-line', color: 'info' }
    cards[3] = { title: '净利润摘要', value: formatMoney(data.dashboard.kpi.netProfit, 'USD'), hint: `毛利率 ${formatPercent(data.dashboard.kpi.grossMargin)}`, icon: 'tabler-coin', color: 'success' }
  }

  return cards
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    home.value = await fetchHome()
    reportData.value = home.value.dashboard ?? null
    if (reportReadable.value) {
      reportPeriods.value = await fetchPeriods()
      if (reportPeriods.value.length && !reportPeriods.value.includes(reportPeriod.value))
        reportPeriod.value = reportPeriods.value[reportPeriods.value.length - 1]!
    }
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '首页数据暂时不可用'
  }
  finally {
    loading.value = false
  }
}

async function loadReport() {
  if (!reportReadable.value)
    return

  reportData.value = await fetchMyDashboard(reportStoreId.value, reportPeriod.value) ?? null
}

onMounted(async () => {
  await load()
  window.setTimeout(() => start(), 500)
})

watch([reportStoreId, reportPeriod], () => {
  if (!loading.value)
    loadReport()
})

function retry() {
  load()
}
</script>

<template>
  <div class="personal-dashboard">
    <section
      id="u2-home-welcome"
      class="personal-dashboard__hero mb-6"
    >
      <div>
        <div class="text-overline text-primary mb-2">
          CrossERP 工作台
        </div>
        <h1 class="text-h4 mb-2">
          {{ session.displayName }}，今天先处理重要的事
        </h1>
        <p class="text-body-1 text-medium-emphasis mb-0">
          {{ roleName }}视图 · 数据会按当前主体的有效权限和数据范围过滤。
        </p>
      </div>
      <div class="d-flex flex-wrap align-center gap-3">
        <VChip
          color="primary"
          variant="tonal"
          prepend-icon="tabler-shield-check"
        >
          权限范围内
        </VChip>
        <VBtn
          variant="tonal"
          prepend-icon="tabler-compass"
          :loading="isRunning"
          @click="restart"
        >
          重新开始引导
        </VBtn>
      </div>
    </section>

    <VAlert
      v-if="error"
      type="warning"
      variant="tonal"
      class="mb-6"
      closable
      @click:close="retry"
    >
      {{ error }}
    </VAlert>

    <LoadingState v-if="loading" />

    <template v-else-if="home">
      <VRow class="mb-1">
        <VCol
          v-for="card in summaryCards"
          :key="card.title"
          cols="12"
          sm="6"
          lg="3"
        >
          <KpiCard
            :title="card.title"
            :value="card.value"
            :hint="card.hint"
            :icon="card.icon"
            :color="card.color"
          />
        </VCol>
      </VRow>

      <VRow>
        <VCol
          cols="12"
          lg="7"
        >
          <VCard class="h-100">
            <VCardItem>
              <template #prepend>
                <VAvatar
                  color="warning"
                  variant="tonal"
                  rounded
                >
                  <VIcon icon="tabler-bell-ringing" />
                </VAvatar>
              </template>
              <VCardTitle>我的待办与提醒</VCardTitle>
              <VCardSubtitle>优先处理当前角色可见的事项</VCardSubtitle>
              <template #append>
                <VBtn
                  v-if="shortcuts.some(item => item.to === '/dashboard/todos')"
                  variant="text"
                  color="primary"
                  to="/dashboard/todos"
                >
                  查看全部
                </VBtn>
              </template>
            </VCardItem>
            <VCardText>
              <VList
                v-if="visibleTasks.length"
                class="py-0"
                lines="two"
              >
                <VListItem
                  v-for="task in visibleTasks"
                  :key="task.id"
                  :to="task.to"
                  rounded="lg"
                  class="mb-2 px-2"
                >
                  <template #prepend>
                    <VAvatar
                      :color="task.kind === 'alert' ? 'error' : 'primary'"
                      variant="tonal"
                      size="36"
                    >
                      <VIcon
                        :icon="task.kind === 'alert' ? 'tabler-alert-triangle' : 'tabler-clipboard-check'"
                        size="19"
                      />
                    </VAvatar>
                  </template>
                  <VListItemTitle class="font-weight-medium">
                    {{ task.title }}
                  </VListItemTitle>
                  <VListItemSubtitle>{{ task.detail }}</VListItemSubtitle>
                  <template #append>
                    <span class="text-caption text-medium-emphasis">{{ task.at || '待处理' }}</span>
                  </template>
                </VListItem>
              </VList>
              <EmptyState
                v-else
                title="暂时没有待办"
                text="新的业务提醒会出现在这里。"
              />
            </VCardText>
          </VCard>
        </VCol>

        <VCol
          cols="12"
          lg="5"
        >
          <VCard class="h-100">
            <VCardItem>
              <template #prepend>
                <VAvatar
                  color="primary"
                  variant="tonal"
                  rounded
                >
                  <VIcon icon="tabler-checkbox" />
                </VAvatar>
              </template>
              <VCardTitle>待审批事项</VCardTitle>
              <VCardSubtitle>审批动作仍按原有职责分离执行</VCardSubtitle>
            </VCardItem>
            <VCardText>
              <VList
                v-if="visibleApprovals.length"
                class="py-0"
                lines="two"
              >
                <VListItem
                  v-for="item in visibleApprovals"
                  :key="item.id"
                  :to="item.to"
                  rounded="lg"
                  class="mb-2 px-2"
                >
                  <VListItemTitle class="font-weight-medium">
                    {{ item.title }}
                  </VListItemTitle>
                  <VListItemSubtitle>{{ item.summary }}</VListItemSubtitle>
                  <template #append>
                    <span class="text-caption text-medium-emphasis">{{ item.submittedAt }}</span>
                  </template>
                </VListItem>
              </VList>
              <EmptyState
                v-else
                title="没有待审批事项"
                text="当前权限范围内没有需要你查看的审批。"
              />
            </VCardText>
          </VCard>
        </VCol>

        <VCol
          cols="12"
          lg="7"
        >
          <VCard class="h-100">
            <VCardItem>
              <template #prepend>
                <VAvatar
                  color="info"
                  variant="tonal"
                  rounded
                >
                  <VIcon icon="tabler-chart-dots-3" />
                </VAvatar>
              </template>
              <VCardTitle>可读数据摘要</VCardTitle>
              <VCardSubtitle>只展示服务层按 scope 返回的数据</VCardSubtitle>
            </VCardItem>
            <VCardText>
              <div class="d-flex flex-wrap gap-3 mb-4">
                <VChip
                  v-for="label in scopeLabels"
                  :key="label"
                  size="small"
                  variant="tonal"
                  color="info"
                >
                  {{ label }}
                </VChip>
                <span
                  v-if="!scopeLabels.length"
                  class="text-body-2 text-medium-emphasis"
                >
                  当前主体没有额外的数据范围标签。
                </span>
              </div>
              <VRow>
                <VCol
                  cols="12"
                  sm="6"
                >
                  <div class="summary-tile">
                    <span class="text-caption text-medium-emphasis">订单记录</span>
                    <strong>{{ formatInteger(home.orders.length) }}</strong>
                    <span class="text-caption text-medium-emphasis">可直接进入订单列表查看</span>
                  </div>
                </VCol>
                <VCol
                  cols="12"
                  sm="6"
                >
                  <div class="summary-tile">
                    <span class="text-caption text-medium-emphasis">费用记录</span>
                    <strong>{{ formatInteger(home.expenses.length) }}</strong>
                    <span class="text-caption text-medium-emphasis">金额由权限 API 返回</span>
                  </div>
                </VCol>
              </VRow>
              <VAlert
                v-if="!aiMode.isEnabled"
                type="info"
                variant="tonal"
                class="mt-4 mb-0"
              >
                智能助手已关闭；你仍可以使用上方待办、审批和业务入口完成工作。
              </VAlert>
            </VCardText>
          </VCard>
        </VCol>

        <VCol
          id="u2-home-shortcuts"
          cols="12"
          lg="5"
        >
          <VCard class="h-100">
            <VCardItem>
              <template #prepend>
                <VAvatar
                  color="success"
                  variant="tonal"
                  rounded
                >
                  <VIcon icon="tabler-layout-grid" />
                </VAvatar>
              </template>
              <VCardTitle>常用入口</VCardTitle>
              <VCardSubtitle>按当前角色显示可用模块</VCardSubtitle>
            </VCardItem>
            <VCardText>
              <VRow>
                <VCol
                  v-for="item in shortcuts"
                  :key="item.to"
                  cols="12"
                  sm="6"
                >
                  <VBtn
                    :to="item.to"
                    variant="tonal"
                    color="primary"
                    block
                    class="shortcut-button justify-start"
                    :prepend-icon="item.icon"
                  >
                    <span class="text-start">
                      <span class="d-block font-weight-medium">{{ item.title }}</span>
                      <span class="d-block text-caption text-medium-emphasis">{{ item.detail }}</span>
                    </span>
                  </VBtn>
                </VCol>
              </VRow>
              <VAlert
                v-if="!shortcuts.length"
                type="info"
                variant="tonal"
                class="mb-0"
              >
                当前角色还没有可用的快捷入口。
              </VAlert>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>

      <section
        v-if="reportReadable && reportData"
        class="mt-8"
      >
        <div class="d-flex flex-wrap justify-space-between align-center gap-4 mb-4">
          <div>
            <h2 class="text-h5 mb-1">
              经营总览
            </h2>
            <p class="text-body-2 text-medium-emphasis mb-0">
              {{ reportData.periodLabel }} · 仅展示当前主体允许店铺的数据
            </p>
          </div>
          <div class="d-flex flex-wrap gap-3">
            <AppSelect
              v-model="reportPeriod"
              :items="reportPeriodItems"
              label="周期"
              style="min-width: 150px;"
            />
            <AppSelect
              v-model="reportStoreId"
              :items="reportStoreItems"
              label="店铺"
              style="min-width: 220px;"
            />
          </div>
        </div>

        <VRow>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="销售额"
              :value="formatMoney(reportData.kpi.sales, 'USD')"
              icon="tabler-currency-dollar"
              color="primary"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="平台费用"
              :value="formatMoney(reportData.kpi.fees, 'USD')"
              icon="tabler-receipt-tax"
              color="warning"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="净利润"
              :value="formatMoney(reportData.kpi.netProfit, 'USD')"
              icon="tabler-chart-line"
              color="success"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="毛利率"
              :value="formatPercent(reportData.kpi.grossMargin)"
              icon="tabler-percentage"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="退款率"
              :value="formatPercent(reportData.kpi.refundRate)"
              icon="tabler-arrow-back"
              color="warning"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="匹配率"
              :value="formatPercent(reportData.kpi.matchRate)"
              icon="tabler-arrows-join"
              color="info"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="待处理异常"
              :value="formatInteger(reportData.kpi.openIssues)"
              icon="tabler-alert-circle"
              color="error"
            />
          </VCol>
          <VCol
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              title="待审批"
              :value="formatInteger(reportData.kpi.pendingApprovals)"
              icon="tabler-checkbox"
              color="secondary"
            />
          </VCol>

          <VCol
            cols="12"
            lg="8"
          >
            <VCard>
              <VCardItem>
                <VCardTitle>趋势</VCardTitle>
                <VCardSubtitle>销售额与净利润</VCardSubtitle>
              </VCardItem>
              <VCardText>
                <VueApexCharts
                  type="area"
                  height="320"
                  :options="trendOptions"
                  :series="trendSeries"
                />
              </VCardText>
            </VCard>
          </VCol>
          <VCol
            cols="12"
            lg="4"
          >
            <VCard class="h-100">
              <VCardItem>
                <VCardTitle>异常原因分布</VCardTitle>
              </VCardItem>
              <VCardText>
                <VueApexCharts
                  v-if="reasonSeries.length"
                  type="donut"
                  height="300"
                  :options="reasonOptions"
                  :series="reasonSeries"
                />
                <EmptyState v-else />
              </VCardText>
            </VCard>
          </VCol>

          <VCol cols="12">
            <VCard>
              <VCardItem>
                <VCardTitle>店铺表现</VCardTitle>
              </VCardItem>
              <VTable>
                <thead>
                  <tr>
                    <th>店铺</th>
                    <th class="text-end">
                      销售额
                    </th>
                    <th class="text-end">
                      净利润
                    </th>
                    <th class="text-end">
                      匹配率
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="store in reportData.stores"
                    :key="store.storeId"
                  >
                    <td>
                      <div class="font-weight-medium">
                        {{ store.storeName }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{ store.platform }} · {{ store.marketplace }}
                      </div>
                    </td>
                    <td class="text-end">
                      {{ formatMoney(store.sales, store.currency) }}
                    </td>
                    <td class="text-end">
                      {{ formatMoney(store.profit, store.currency) }}
                    </td>
                    <td class="text-end">
                      {{ formatPercent(store.matchRate) }}
                    </td>
                  </tr>
                </tbody>
              </VTable>
            </VCard>
          </VCol>
        </VRow>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.personal-dashboard__hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.5rem;
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  border-radius: 20px;
  background:
    radial-gradient(circle at 90% 20%, rgba(var(--v-theme-primary), 0.14), transparent 34%),
    rgb(var(--v-theme-surface));
}

.summary-tile {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-block-size: 112px;
  padding: 1rem;
  border-radius: 14px;
  background: rgba(var(--v-theme-on-surface), 0.035);

  strong {
    color: rgb(var(--v-theme-on-surface));
    font-size: 1.5rem;
    line-height: 1.2;
  }
}

.shortcut-button {
  min-block-size: 74px;
  padding: 0.75rem 1rem;
  text-transform: none;
}

@media (max-width: 600px) {
  .personal-dashboard__hero {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
