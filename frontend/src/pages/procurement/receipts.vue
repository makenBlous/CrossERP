<script setup lang="ts">
import { fetchReceipts } from '@/api/procurement'
import ListPage from '@/components/biz/ListPage.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { ReceiptRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const rows = ref<ReceiptRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchReceipts()
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
  { key: 'no', title: t('inventory.docNo') },
  { key: 'purchaseOrderNo', title: t('procurement.ordersTitle') },
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'receivedAt', title: t('orders.date') },
  { key: 'qty', title: t('procurement.receivedQty'), align: 'end' as const },
  { key: 'orderedQty', title: t('procurement.orderedQty'), align: 'end' as const },
  { key: 'variance', title: t('procurement.diff'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
])

const filters = computed(() => [{
  key: 'warehouseName',
  label: t('inventory.warehouse'),
  items: [...new Set(rows.value.map(item => item.warehouseName))].map(name => ({ title: name, value: name })),
}])

function openRow(row: ReceiptRow) {
  setSelected(row.purchaseOrderId)
  router.push({ path: `/procurement/orders/${row.purchaseOrderId}` })
}
</script>

<template>
  <ListPage
    storage-key="procurement-receipts"
    :title="t('procurement.receiptsTitle')"
    :subtitle="t('procurement.receiptsSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    date-key="receivedAt"
    :loading="loading"
    :error="error"
    @retry="load"
    @open="openRow"
  >
    <template #item.status="{ item }">
      <StatusChip
        domain="receipt"
        :value="item.status"
      />
    </template>
  </ListPage>
</template>
