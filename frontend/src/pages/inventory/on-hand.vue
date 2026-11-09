<script setup lang="ts">
import { fetchOnHand } from '@/api/inventory'
import ListPage from '@/components/biz/ListPage.vue'
import type { InventoryTotals, OnHandRow } from '@/types/domain'
import { formatInteger } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<OnHandRow[]>([])
const totals = ref<InventoryTotals | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const payload = await fetchOnHand()

    rows.value = payload.rows
    totals.value = payload.totals
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const filters = computed(() => [{
  key: 'alert',
  label: t('inventory.alert'),
  items: [
    { title: t('inventory.ok'), value: 'ok' },
    { title: t('inventory.lowTag'), value: 'low' },
    { title: t('inventory.stockoutTag'), value: 'stockout' },
  ],
}])

const items = computed(() => rows.value.map(row => ({ ...row, id: row.sku })))

const columns = computed(() => [
  { key: 'sku', title: t('orders.sku') },
  { key: 'name', title: t('inventory.name') },
  { key: 'fbaQty', title: t('inventory.fbaQty'), align: 'end' as const },
  { key: 'overseasQty', title: t('inventory.overseasQty'), align: 'end' as const },
  { key: 'domesticQty', title: t('inventory.domesticQty'), align: 'end' as const },
  { key: 'coverDays', title: t('inventory.coverDays'), align: 'end' as const },
  { key: 'alert', title: t('inventory.alert') },
])
</script>

<template>
  <ListPage
    storage-key="inventory-on-hand"
    :title="t('inventory.title')"
    :subtitle="t('inventory.subtitle')"
    :items="items"
    :columns="columns"
    :filters="filters"
    :loading="loading"
    :error="error"
    @retry="load"
  >
    <template #widgets>
      <VRow
        v-if="totals"
        class="mb-6"
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
    </template>
    <template #item.sku="{ item }">
      <div class="font-weight-medium">
        {{ item.sku }}
      </div>
      <div class="text-caption text-medium-emphasis">
        {{ item.fbaWarehouse }}
      </div>
    </template>
    <template #item.alert="{ item }">
      <StatusChip
        domain="stock_alert"
        :value="item.alert"
      />
    </template>
  </ListPage>
</template>
