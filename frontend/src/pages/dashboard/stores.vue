<script setup lang="ts">
import type { ApexOptions } from 'apexcharts'
import { fetchDashboard, fetchPeriods } from '@/api/dashboard'
import ListPage from '@/components/biz/ListPage.vue'
import { useChartTheme } from '@/composables/useChartTheme'
import type { StoreRank } from '@/types/domain'
import { formatMoney, formatPercent } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const chart = useChartTheme()
const period = ref('2026-10')
const periods = ref<string[]>([])
const rows = ref<Array<StoreRank & { id: string; salesText: string; profitText: string; matchText: string }>>([])
const loading = ref(true)
const error = ref('')

const periodItems = computed(() => periods.value.map(item => ({ title: item, value: item })))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchDashboard('all', period.value)

    rows.value = data.stores.map(item => ({
      ...item,
      id: item.storeId,
      salesText: formatMoney(item.sales, item.currency),
      profitText: formatMoney(item.profit, item.currency),
      matchText: formatPercent(item.matchRate),
    }))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(async () => {
  periods.value = await fetchPeriods()
  await load()
})

watch(period, load)

const columns = computed(() => [
  { key: 'storeName', title: t('common.store') },
  { key: 'platform', title: t('orders.platform') },
  { key: 'marketplace', title: t('common.store') },
  { key: 'salesText', title: t('dashboard.sales'), align: 'end' as const },
  { key: 'profitText', title: t('dashboard.netProfit'), align: 'end' as const },
  { key: 'matchText', title: t('dashboard.matchRate'), align: 'end' as const },
])

const filters = computed(() => [{
  key: 'platform',
  label: t('orders.platform'),
  items: [...new Set(rows.value.map(item => item.platform))].map(name => ({ title: name, value: name })),
}])

const chartOptions = computed<ApexOptions>(() => ({
  chart: { toolbar: { show: false }, fontFamily: 'inherit' },
  plotOptions: { bar: { borderRadius: 4, columnWidth: '48%' } },
  colors: [chart.primary.value, chart.success.value],
  dataLabels: { enabled: false },
  xaxis: {
    categories: rows.value.map(item => item.storeName),
    labels: { style: { colors: chart.label.value } },
  },
  yaxis: { labels: { style: { colors: chart.label.value } } },
  grid: { borderColor: chart.grid.value },
  legend: { labels: { colors: chart.label.value } },
}))

const series = computed(() => [
  { name: t('dashboard.salesSeries'), data: rows.value.map(item => item.sales) },
  { name: t('dashboard.profitSeries'), data: rows.value.map(item => item.profit) },
])
</script>

<template>
  <div>
    <div class="d-flex justify-end mb-4">
      <AppSelect
        v-model="period"
        :items="periodItems"
        :label="t('dashboard.period')"
        style="max-width: 220px;"
      />
    </div>
    <VCard class="mb-6">
      <VCardItem>
        <VCardTitle>{{ t('dashboard.storesLink') }}</VCardTitle>
        <VCardSubtitle>{{ t('dashboard.reporting') }}</VCardSubtitle>
      </VCardItem>
      <VCardText>
        <VueApexCharts
          type="bar"
          height="320"
          :options="chartOptions"
          :series="series"
        />
      </VCardText>
    </VCard>
    <ListPage
      storage-key="dashboard-stores"
      :title="t('dashboard.storesLink')"
      :subtitle="t('dashboard.reporting')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="[{ key: 'ready', label: t('foundation.exportCsv') }]"
      @retry="load"
    />
  </div>
</template>
