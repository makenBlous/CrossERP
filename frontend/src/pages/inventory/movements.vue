<script setup lang="ts">
import { fetchMovements } from '@/api/inventory'
import ListPage from '@/components/biz/ListPage.vue'
import type { MovementRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<MovementRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchMovements()
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
  { key: 'occurredAt', title: t('orders.date') },
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'internalSku', title: t('inventory.sku') },
  { key: 'qtyDelta', title: t('inventory.qtyDelta'), align: 'end' as const },
  { key: 'inTransitDelta', title: t('inventory.transitDelta'), align: 'end' as const },
  { key: 'reason', title: t('inventory.reason') },
  { key: 'refId', title: t('inventory.ref') },
  { key: 'createdBy', title: t('inventory.actor') },
])

const filters = computed(() => [
  {
    key: 'warehouseName',
    label: t('inventory.warehouse'),
    items: [...new Set(rows.value.map(item => item.warehouseName))].map(name => ({ title: name, value: name })),
  },
  {
    key: 'reason',
    label: t('inventory.reason'),
    items: [...new Set(rows.value.map(item => item.reason))].map(name => ({ title: name, value: name })),
  },
])
</script>

<template>
  <ListPage
    storage-key="inventory-movements"
    :title="t('inventory.movementsTitle')"
    :subtitle="t('inventory.movementsSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    date-key="occurredAt"
    :loading="loading"
    :error="error"
    @retry="load"
  />
</template>
