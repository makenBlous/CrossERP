<script setup lang="ts">
import { fetchOrders } from '@/api/orders'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { OrderSummary } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const orders = ref<OrderSummary[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    orders.value = await fetchOrders()
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
  { key: 'orderNo', title: t('orders.orderNo') },
  { key: 'storeName', title: t('common.store') },
  { key: 'orderedAt', title: t('orders.date') },
  { key: 'status', title: t('common.status') },
  { key: 'fulfillment', title: t('orders.fulfillment') },
  { key: 'itemTotal', title: t('orders.itemTotal'), align: 'end' as const },
  { key: 'net', title: t('orders.net'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => {
  const names = [...new Set(orders.value.map(item => item.storeName))]

  return [{
    key: 'storeName',
    label: t('common.store'),
    items: names.map(name => ({ title: name, value: name })),
  }]
})
</script>

<template>
  <ListPage
    storage-key="orders"
    :title="t('orders.title')"
    :subtitle="`${t('orders.subtitle')} ${t('common.fromSystem')}`"
    :items="orders"
    :columns="columns"
    :filters="filters"
    date-key="orderedAt"
    :loading="loading"
    :error="error"
    @retry="load"
  >
    <template #item.status="{ item }">
      <StatusChip
        domain="sales_order"
        :value="item.statusCode || ''"
      />
    </template>
    <template #item.itemTotal="{ item }">
      <MoneyText
        :amount="item.itemTotal"
        :currency="item.currency"
      />
    </template>
    <template #item.net="{ item }">
      <MoneyText
        :amount="item.net"
        :currency="item.currency"
      />
    </template>
    <template #item.actions="{ item }">
      <VBtn
        size="small"
        variant="text"
        :to="{ path: `/orders/${item.id}` }"
      >
        {{ t('common.view') }}
      </VBtn>
    </template>
  </ListPage>
</template>
