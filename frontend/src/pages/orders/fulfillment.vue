<script setup lang="ts">
import { fetchFulfillment } from '@/api/orders'
import { shipSalesOrders } from '@/api/workflows'
import ListPage from '@/components/biz/ListPage.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { FulfillmentRow } from '@/types/domain'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { setSelected } = usePageContext()
const rows = ref<FulfillmentRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchFulfillment()
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
  { key: 'status', title: t('common.status') },
  { key: 'fulfillment', title: t('orders.fulfillment') },
  { key: 'warehouse', title: t('orders.warehouse') },
  { key: 'carrier', title: t('orders.carrier') },
  { key: 'trackingNo', title: t('orders.tracking') },
  { key: 'shippedAt', title: t('orders.shippedAt') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'status', label: t('common.status'), items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })) },
  { key: 'fulfillment', label: t('orders.fulfillment'), items: [...new Set(rows.value.map(item => item.fulfillment))].map(name => ({ title: name, value: name })) },
])

const batchActions = computed(() => can(session.role, 'ship')
  ? [{ key: 'ship', label: t('orders.shipBatch') }]
  : [])

function openRow(row: FulfillmentRow) {
  setSelected(row.id)
  router.push({ path: `/orders/${row.id}` })
}

async function onBatch(_action: string, selected: FulfillmentRow[]) {
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
      storage-key="order-fulfillment"
      :title="t('orders.fulfillmentTitle')"
      :subtitle="t('orders.fulfillmentSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="shippedAt"
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
          :value="item.status"
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
