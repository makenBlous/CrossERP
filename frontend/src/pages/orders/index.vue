<script setup lang="ts">
import { fetchOrders } from '@/api/orders'
import { shipSalesOrders } from '@/api/workflows'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { OrderSummary } from '@/types/domain'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { setSelected } = usePageContext()
const orders = ref<OrderSummary[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')

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
  { key: 'platform', title: t('orders.platform') },
  { key: 'orderedAt', title: t('orders.date') },
  { key: 'status', title: t('common.status') },
  { key: 'fulfillment', title: t('orders.fulfillment') },
  { key: 'itemTotal', title: t('orders.itemTotal'), align: 'end' as const },
  { key: 'net', title: t('orders.net'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => {
  const names = [...new Set(orders.value.map(item => item.storeName))]
  const platforms = [...new Set(orders.value.map(item => item.platform))]

  return [
    { key: 'storeName', label: t('common.store'), items: names.map(name => ({ title: name, value: name })) },
    { key: 'platform', label: t('orders.platform'), items: platforms.map(name => ({ title: name, value: name })) },
    { key: 'status', label: t('common.status'), items: [...new Set(orders.value.map(item => item.status))].map(name => ({ title: name, value: name })) },
  ]
})

const batchActions = computed(() => can(session.role, 'ship')
  ? [{ key: 'ship', label: t('orders.shipBatch') }]
  : [])

function openRow(row: OrderSummary) {
  setSelected(row.id)
  router.push({ path: `/orders/${row.id}` })
}

async function onBatch(_action: string, selected: OrderSummary[]) {
  message.value = ''
  try {
    const failed = await shipSalesOrders(selected.map(item => item.id))

    if (failed.length)
      message.value = failed.join('；')

    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
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
      :batch-actions="batchActions"
      @retry="load"
      @open="openRow"
      @batch="onBatch"
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
  </div>
</template>
