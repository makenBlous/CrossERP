<script setup lang="ts">
import type { ApexOptions } from 'apexcharts'
import { draftVoucherFromProfit, fetchProfit } from '@/api/finance'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useChartTheme } from '@/composables/useChartTheme'
import type { ProfitRow, StoreProfit } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const chart = useChartTheme()
const rows = ref<ProfitRow[]>([])
const stores = ref<StoreProfit[]>([])
const router = useRouter()

onMounted(async () => {
  const payload = await fetchProfit()

  rows.value = payload.rows
  stores.value = payload.stores
})

const chartOptions = computed<ApexOptions>(() => ({
  chart: { toolbar: { show: false }, fontFamily: 'inherit' },
  plotOptions: { bar: { borderRadius: 6, columnWidth: '42%' } },
  colors: [chart.success.value],
  dataLabels: { enabled: false },
  xaxis: {
    categories: stores.value.map(item => item.storeName),
    labels: { style: { colors: chart.label.value } },
  },
  yaxis: { labels: { style: { colors: chart.label.value } } },
  grid: { borderColor: chart.grid.value },
}))

const chartSeries = computed(() => [
  { name: t('profit.profit'), data: stores.value.map(item => item.profit) },
])

const skuItems = computed(() => rows.value.map(row => ({
  ...row,
  id: `${row.sku}-${row.storeId}`,
})))

const skuColumns = computed(() => [
  { key: 'sku', title: t('orders.sku') },
  { key: 'storeName', title: t('common.store') },
  { key: 'revenue', title: t('profit.revenue'), align: 'end' as const },
  { key: 'platformFee', title: t('profit.platformFee'), align: 'end' as const },
  { key: 'ads', title: t('profit.ads'), align: 'end' as const },
  { key: 'firstMile', title: t('profit.firstMile'), align: 'end' as const },
  { key: 'cost', title: t('profit.cost'), align: 'end' as const },
  { key: 'profit', title: t('profit.profit'), align: 'end' as const },
])
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('profit.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('profit.subtitle') }}
      </p>
    </div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      {{ t('profit.formula') }}
    </VAlert>
    <VRow class="mb-6">
      <VCol
        cols="12"
        sm="4"
      >
        <KpiCard
          title="SKU 行数"
          :value="String(rows.length)"
          icon="tabler-chart-bar"
        />
      </VCol>
      <VCol
        cols="12"
        sm="4"
      >
        <KpiCard
          title="店铺数"
          :value="String(stores.length)"
          icon="tabler-building-store"
          color="info"
        />
      </VCol>
      <VCol
        cols="12"
        sm="4"
      >
        <KpiCard
          title="广告来源"
          value="广告分摊 / 演示计提"
          icon="tabler-speakerphone"
          color="success"
        />
      </VCol>
    </VRow>
    <div class="d-flex justify-end mb-4">
      <VBtn
        variant="tonal"
        prepend-icon="tabler-notebook"
        @click="draftVoucherFromProfit().then(voucher => voucher && router.push(`/finance/vouchers/${voucher.id}`))"
      >
        生成凭证草稿
      </VBtn>
    </div>
    <VCard class="mb-6">
      <VCardItem>
        <VCardTitle>{{ t('profit.chart') }}</VCardTitle>
        <VCardSubtitle>{{ t('profit.byStore') }}</VCardSubtitle>
      </VCardItem>
      <VCardText>
        <VueApexCharts
          type="bar"
          height="300"
          :options="chartOptions"
          :series="chartSeries"
        />
      </VCardText>
    </VCard>
    <VCard class="mb-6">
      <VCardItem>
        <VCardTitle>{{ t('profit.byStore') }}</VCardTitle>
      </VCardItem>
      <VTable>
        <thead>
          <tr>
            <th>{{ t('common.store') }}</th>
            <th class="text-end">
              {{ t('profit.revenue') }}
            </th>
            <th class="text-end">
              {{ t('profit.platformFee') }}
            </th>
            <th class="text-end">
              {{ t('profit.ads') }}
            </th>
            <th class="text-end">
              {{ t('profit.firstMile') }}
            </th>
            <th class="text-end">
              {{ t('profit.cost') }}
            </th>
            <th class="text-end">
              {{ t('profit.profit') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="store in stores"
            :key="store.storeId"
          >
            <td>{{ store.storeName }}</td>
            <td class="text-end">
              <MoneyText
                :amount="store.revenue"
                :currency="store.currency"
                minor
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="store.platformFee"
                :currency="store.currency"
                minor
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="store.ads"
                :currency="store.currency"
                minor
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="store.firstMile"
                :currency="store.currency"
                minor
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="store.cost"
                :currency="store.currency"
                minor
              />
            </td>
            <td class="text-end font-weight-medium">
              <MoneyText
                :amount="store.profit"
                :currency="store.currency"
                minor
              />
            </td>
          </tr>
        </tbody>
      </VTable>
    </VCard>
    <ListPage
      embedded
      storage-key="finance-profit-sku"
      :title="t('profit.bySku')"
      :items="skuItems"
      :columns="skuColumns"
      @open="item => router.push(`/finance/profit/sku/${item.sku}`)"
    >
      <template #item.revenue="{ item }">
        <MoneyText
          :amount="item.revenue"
          :currency="item.currency"
          minor
        />
      </template>
      <template #item.platformFee="{ item }">
        <MoneyText
          :amount="item.platformFee"
          :currency="item.currency"
          minor
        />
      </template>
      <template #item.ads="{ item }">
        <MoneyText
          :amount="item.ads"
          :currency="item.currency"
          minor
        />
      </template>
      <template #item.firstMile="{ item }">
        <MoneyText
          :amount="item.firstMile"
          :currency="item.currency"
          minor
        />
      </template>
      <template #item.cost="{ item }">
        <MoneyText
          :amount="item.cost"
          :currency="item.currency"
          minor
        />
      </template>
      <template #item.profit="{ item }">
        <MoneyText
          :amount="item.profit"
          :currency="item.currency"
          minor
        />
      </template>
    </ListPage>
  </div>
</template>
