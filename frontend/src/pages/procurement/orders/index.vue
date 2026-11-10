<script setup lang="ts">
import { fetchPurchaseOrders } from '@/api/procurement'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { PurchaseOrderRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const rows = ref<PurchaseOrderRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchPurchaseOrders()
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
  { key: 'supplierName', title: t('procurement.supplier') },
  { key: 'status', title: t('common.status') },
  { key: 'expectedAt', title: t('procurement.due') },
  { key: 'amount', title: t('procurement.amount'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  {
    key: 'supplierName',
    label: t('procurement.supplier'),
    items: [...new Set(rows.value.map(item => item.supplierName))].map(name => ({ title: name, value: name })),
  },
  {
    key: 'status',
    label: t('common.status'),
    items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
  },
])

function openRow(row: PurchaseOrderRow) {
  setSelected(row.id)
  router.push({ path: `/procurement/orders/${row.id}` })
}
</script>

<template>
  <div>
    <ListPage
      storage-key="procurement-orders"
      :title="t('procurement.ordersTitle')"
      :subtitle="t('procurement.ordersSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="expectedAt"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            color="primary"
            :to="{ path: '/procurement/orders/new' }"
          >
            {{ t('procurement.newOrder') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="purchase_order"
          :value="item.status"
        />
      </template>
      <template #item.amount="{ item }">
        <MoneyText
          :amount="item.amount"
          :currency="item.currency"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/procurement/orders/${item.id}` }"
        >
          {{ t('common.view') }}
        </VBtn>
      </template>
    </ListPage>
  </div>
</template>
