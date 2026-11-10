<script setup lang="ts">
import { fetchStockLedger } from '@/api/fin-cost'
import AuditActorId from '@/components/biz/AuditActorId.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { LedgerRow } from '@/mocks/services/fin-cost'
import { canPermission } from '@/api/mock-client'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<LedgerRow[]>([])
const loading = ref(true)
const error = ref('')
const canSeeCost = computed(() => canPermission('sku.cost:read'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchStockLedger()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const costColumns = computed(() => {
  if (!canSeeCost.value)
    return []

  return [
    { key: 'amountDelta', title: t('inventory.amountDelta'), align: 'end' as const },
    { key: 'balanceAmount', title: t('inventory.balanceAmount'), align: 'end' as const },
  ]
})

const columns = computed(() => [
  { key: 'occurredAt', title: t('inventory.ledgerDate') },
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'internalSku', title: t('inventory.sku') },
  { key: 'batch', title: t('inventory.ledgerBatch') },
  { key: 'qtyDelta', title: t('inventory.qtyDelta'), align: 'end' as const },
  ...costColumns.value.slice(0, 1),
  { key: 'balanceQty', title: t('inventory.balanceQty'), align: 'end' as const },
  ...costColumns.value.slice(1),
  { key: 'valuationMethod', title: t('inventory.valuationMethod') },
  { key: 'refId', title: t('inventory.ref') },
  { key: 'actorId', title: t('inventory.actor') },
])

const filters = computed(() => [
  {
    key: 'warehouseName',
    label: t('inventory.warehouse'),
    items: [...new Set(rows.value.map(item => item.warehouseName))].map(value => ({ title: value, value })),
  },
  {
    key: 'internalSku',
    label: t('inventory.sku'),
    items: [...new Set(rows.value.map(item => item.internalSku))].map(value => ({ title: value, value })),
  },
])
</script>

<template>
  <VAlert
    type="info"
    variant="tonal"
    class="mb-4"
  >
    {{ t('inventory.ledgerNotice') }}
  </VAlert>
  <ListPage
    storage-key="inventory-ledger"
    :title="t('inventory.ledgerTitle')"
    :subtitle="t('inventory.ledgerSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    date-key="occurredAt"
    :loading="loading"
    :error="error"
    @retry="load"
  >
    <template #item.amountDelta="{ item }">
      <MoneyText
        v-if="item.amountDelta != null"
        :amount="item.amountDelta"
        minor
        currency="CNY"
      />
      <span v-else>—</span>
    </template>
    <template #item.balanceAmount="{ item }">
      <MoneyText
        v-if="item.balanceAmount != null"
        :amount="item.balanceAmount"
        minor
        currency="CNY"
      />
      <span v-else>—</span>
    </template>
    <template #item.valuationMethod="{ item }">
      <VChip
        size="small"
        color="info"
        variant="tonal"
      >
        {{ item.valuationMethod === 'moving_average' ? t('inventory.movingAverage') : item.valuationMethod }}
      </VChip>
    </template>
    <template #item.actorId="{ item }">
      <AuditActorId :actor-id="item.actorId" />
    </template>
  </ListPage>
</template>
