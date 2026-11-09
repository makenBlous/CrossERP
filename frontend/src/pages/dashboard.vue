<script setup lang="ts">
import type { ApexOptions } from 'apexcharts'
import { fetchDashboard, fetchStores } from '@/api/dashboard'
import { useChartTheme } from '@/composables/useChartTheme'
import type { DashboardPayload, Store } from '@/types/domain'
import { formatInteger, formatMoney, formatPercent } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const chart = useChartTheme()
const storeId = ref('all')
const stores = ref<Store[]>([])
const data = ref<DashboardPayload | null>(null)

const storeItems = computed(() => [
  { title: t('common.allStores'), value: 'all' },
  ...stores.value.map(item => ({ title: `${item.name} · ${item.marketplace}`, value: item.id })),
])

async function load() {
  data.value = await fetchDashboard(storeId.value)
}

onMounted(async () => {
  stores.value = await fetchStores()
  await load()
})

watch(storeId, () => {
  load()
})

const trendOptions = computed<ApexOptions>(() => ({
  chart: { toolbar: { show: false }, parentHeightOffset: 0, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 3 },
  colors: [chart.primary.value, chart.success.value],
  dataLabels: { enabled: false },
  xaxis: {
    categories: data.value?.trend.map(item => item.month) ?? [],
    labels: { style: { colors: chart.label.value } },
  },
  yaxis: { labels: { style: { colors: chart.label.value } } },
  grid: { borderColor: chart.grid.value },
  legend: { labels: { colors: chart.label.value } },
  tooltip: { theme: chart.label.value.includes('225') ? 'dark' : 'light' },
}))

const trendSeries = computed(() => [
  { name: t('dashboard.salesSeries'), data: data.value?.trend.map(item => item.sales) ?? [] },
  { name: t('dashboard.profitSeries'), data: data.value?.trend.map(item => item.profit) ?? [] },
])

const reasonOptions = computed<ApexOptions>(() => ({
  labels: data.value?.reasons.map(item => item.code) ?? [],
  colors: [chart.error.value, chart.warning.value, chart.info.value, chart.primary.value],
  legend: { position: 'bottom', labels: { colors: chart.label.value } },
  dataLabels: { enabled: false },
  stroke: { width: 0 },
}))

const reasonSeries = computed(() => data.value?.reasons.map(item => item.count) ?? [])

const shortcuts = [
  { to: '/finance/issues', icon: 'tabler-alert-circle', key: 'issues.title' },
  { to: '/finance/profit', icon: 'tabler-chart-line', key: 'profit.title' },
  { to: '/approvals', icon: 'tabler-checkbox', key: 'approvals.title' },
  { to: '/finance/recon', icon: 'tabler-arrows-join', key: 'recon.title' },
  { to: '/orders', icon: 'tabler-receipt', key: 'orders.title' },
  { to: '/agent/chat', icon: 'tabler-message-chatbot', key: 'chat.title' },
]
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-center gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          {{ t('dashboard.title') }}
        </h4>
        <p class="text-body-1 text-medium-emphasis mb-0">
          {{ t('dashboard.subtitle') }}
        </p>
      </div>
      <AppSelect
        v-model="storeId"
        :items="storeItems"
        :label="t('common.store')"
        style="min-width: 260px;"
      />
    </div>

    <VRow v-if="data">
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('dashboard.sales')"
          :value="formatMoney(data.kpi.sales, 'USD')"
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
          :title="t('dashboard.netProfit')"
          :value="formatMoney(data.kpi.netProfit, 'USD')"
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
          :title="t('dashboard.grossMargin')"
          :value="formatPercent(data.kpi.grossMargin)"
          icon="tabler-percentage"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('dashboard.refundRate')"
          :value="formatPercent(data.kpi.refundRate)"
          icon="tabler-arrow-back"
          color="warning"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="4"
      >
        <KpiCard
          :title="t('dashboard.matchRate')"
          :value="formatPercent(data.kpi.matchRate)"
          icon="tabler-arrows-join"
          color="info"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="4"
      >
        <KpiCard
          :title="t('dashboard.openIssues')"
          :value="formatInteger(data.kpi.openIssues)"
          icon="tabler-alert-circle"
          color="error"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="4"
      >
        <KpiCard
          :title="t('dashboard.pendingApprovals')"
          :value="formatInteger(data.kpi.pendingApprovals)"
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
            <VCardTitle>{{ t('dashboard.trend') }}</VCardTitle>
            <VCardSubtitle>{{ data.periodLabel }} · {{ t('dashboard.reporting') }}</VCardSubtitle>
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
            <VCardTitle>{{ t('dashboard.reasonDist') }}</VCardTitle>
          </VCardItem>
          <VCardText>
            <VueApexCharts
              type="donut"
              height="300"
              :options="reasonOptions"
              :series="reasonSeries"
            />
          </VCardText>
        </VCard>
      </VCol>

      <VCol
        cols="12"
        lg="8"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>{{ t('dashboard.storeRank') }}</VCardTitle>
          </VCardItem>
          <VTable>
            <thead>
              <tr>
                <th>{{ t('common.store') }}</th>
                <th class="text-end">
                  {{ t('dashboard.sales') }}
                </th>
                <th class="text-end">
                  {{ t('dashboard.netProfit') }}
                </th>
                <th class="text-end">
                  {{ t('dashboard.matchRate') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="store in data.stores"
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
      <VCol
        cols="12"
        lg="4"
      >
        <VCard class="h-100">
          <VCardItem>
            <VCardTitle>{{ t('dashboard.shortcuts') }}</VCardTitle>
          </VCardItem>
          <VCardText class="d-flex flex-column gap-3">
            <VBtn
              v-for="item in shortcuts"
              :key="item.to"
              :to="item.to"
              variant="tonal"
              block
              :prepend-icon="item.icon"
            >
              {{ t(item.key) }}
            </VBtn>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
