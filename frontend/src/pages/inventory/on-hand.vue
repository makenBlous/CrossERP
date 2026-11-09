<script setup lang="ts">
import { fetchOnHand } from '@/api/inventory'
import type { InventoryTotals, OnHandRow, StockAlert } from '@/types/domain'
import { formatInteger } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<OnHandRow[]>([])
const totals = ref<InventoryTotals | null>(null)

onMounted(async () => {
  const payload = await fetchOnHand()

  rows.value = payload.rows
  totals.value = payload.totals
})

const headers = computed(() => [
  { title: t('orders.sku'), key: 'sku' },
  { title: t('inventory.name'), key: 'name' },
  { title: t('inventory.fbaQty'), key: 'fbaQty', align: 'end' as const },
  { title: t('inventory.overseasQty'), key: 'overseasQty', align: 'end' as const },
  { title: t('inventory.domesticQty'), key: 'domesticQty', align: 'end' as const },
  { title: t('inventory.coverDays'), key: 'coverDays', align: 'end' as const },
  { title: t('inventory.alert'), key: 'alert' },
])

function alertLabel(alert: StockAlert) {
  if (alert === 'stockout')
    return t('inventory.stockoutTag')
  if (alert === 'low')
    return t('inventory.lowTag')

  return t('inventory.ok')
}

function alertColor(alert: StockAlert) {
  if (alert === 'stockout')
    return 'error'
  if (alert === 'low')
    return 'warning'

  return 'success'
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('inventory.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('inventory.subtitle') }}
      </p>
    </div>
    <VRow
      v-if="totals"
      class="mb-2"
    >
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('inventory.fba')"
          :value="formatInteger(totals.fbaQty)"
          icon="tabler-brand-amazon"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('inventory.overseas')"
          :value="formatInteger(totals.overseasQty)"
          icon="tabler-world"
          color="info"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('inventory.domestic')"
          :value="formatInteger(totals.domesticQty)"
          icon="tabler-home"
          color="success"
        />
      </VCol>
      <VCol
        cols="12"
        sm="6"
        lg="3"
      >
        <KpiCard
          :title="t('inventory.low')"
          :value="`${totals.lowSku} / ${t('inventory.stockout')} ${totals.stockoutSku}`"
          icon="tabler-alert-triangle"
          color="warning"
        />
      </VCol>
    </VRow>
    <VCard>
      <VDataTable
        :headers="headers"
        :items="rows"
        :items-per-page="10"
      >
        <template #item.sku="{ item }">
          <div class="font-weight-medium">
            {{ item.sku }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{ item.fbaWarehouse }}
          </div>
        </template>
        <template #item.alert="{ item }">
          <VChip
            size="small"
            :color="alertColor(item.alert)"
          >
            {{ alertLabel(item.alert) }}
          </VChip>
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
