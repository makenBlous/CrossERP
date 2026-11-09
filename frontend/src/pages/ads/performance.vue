<script setup lang="ts">
import type { ApexOptions } from 'apexcharts'
import { fetchAdPerformance } from '@/api/ads'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'
import { useChartTheme } from '@/composables/useChartTheme'

const chart = useChartTheme()
const rows = ref<Awaited<ReturnType<typeof fetchAdPerformance>>>([])

onMounted(async () => {
  rows.value = await fetchAdPerformance()
})

const columns = [{ key: 'name', title: '活动' }, { key: 'storeName', title: '店铺' }, { key: 'spendDisplay', title: '花费' }, { key: 'salesDisplay', title: '销售额' }, { key: 'roas', title: 'ROAS' }]
const options = computed<ApexOptions>(() => ({ chart: { toolbar: { show: false } }, colors: [chart.primary.value], xaxis: { categories: rows.value.map(row => row.name) }, grid: { borderColor: chart.grid.value } }))
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        广告效果
      </h4><p class="text-body-1 text-medium-emphasis mb-0">
        花费与已存储销售结果对照。
      </p>
    </div><VCard class="mb-6">
      <VCardText>
        <VueApexCharts
          type="bar"
          height="280"
          :options="options"
          :series="[{ name: '花费', data: rows.map(row => row.spendDisplay) }, { name: '销售额', data: rows.map(row => row.salesDisplay) }]"
        />
      </VCardText>
    </VCard><FinanceTablePage
      storage-key="ads-performance"
      title="活动表现"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    >
      <template #item.salesDisplay="{ item }">
        <MoneyText
          :amount="Number(item.sales)"
          :currency="String(item.currency) as 'USD'"
          minor
        />
      </template>
    </FinanceTablePage>
  </div>
</template>
