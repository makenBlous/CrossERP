<script setup lang="ts">
import { fetchChannels } from '@/api/orders'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { ChannelRow } from '@/types/domain'
import { formatInteger } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<ChannelRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchChannels()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const columns = computed(() => [
  { key: 'platform', title: t('orders.platform') },
  { key: 'currency', title: t('common.amount') },
  { key: 'orders', title: t('orders.orderCount') },
  { key: 'sales', title: t('orders.sales'), align: 'end' as const },
  { key: 'refunds', title: t('orders.refunds'), align: 'end' as const },
])

const filters = computed(() => [{
  key: 'platform',
  label: t('orders.platform'),
  items: [...new Set(rows.value.map(item => item.platform))].map(name => ({ title: name, value: name })),
}])

const totals = computed(() => ({
  orders: rows.value.reduce((sum, item) => sum + item.orders, 0),
  platforms: new Set(rows.value.map(item => item.platform)).size,
}))
</script>

<template>
  <div>
    <VRow class="mb-2">
      <VCol
        cols="12"
        sm="6"
      >
        <KpiCard
          :title="t('orders.orderCount')"
          :value="formatInteger(totals.orders)"
          icon="tabler-receipt"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
      >
        <KpiCard
          :title="t('orders.platform')"
          :value="formatInteger(totals.platforms)"
          icon="tabler-chart-bar"
          color="info"
        />
      </VCol>
    </VRow>
    <ListPage
      storage-key="order-channels"
      :title="t('orders.channelsTitle')"
      :subtitle="t('orders.channelsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="[{ key: 'note', label: t('foundation.exportCsv') }]"
      @retry="load"
    >
      <template #item.sales="{ item }">
        <MoneyText
          :amount="item.sales"
          :currency="item.currency"
        />
      </template>
      <template #item.refunds="{ item }">
        <MoneyText
          :amount="item.refunds"
          :currency="item.currency"
        />
      </template>
    </ListPage>
  </div>
</template>
