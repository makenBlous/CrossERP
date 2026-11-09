<script setup lang="ts">
import { fetchBalances } from '@/api/inventory'
import ListPage from '@/components/biz/ListPage.vue'
import type { BalanceRow } from '@/types/domain'
import { formatInteger } from '@/utils/format'

const props = defineProps<{
  kind: 'fba' | 'overseas' | 'domestic'
  storageKey: string
}>()

const { t } = useI18n({ useScope: 'global' })
const rows = ref<BalanceRow[]>([])
const loading = ref(true)
const error = ref('')

const titleKey = {
  fba: 'inventory.fbaTitle',
  overseas: 'inventory.overseasTitle',
  domestic: 'inventory.domesticTitle',
} as const

const subtitleKey = {
  fba: 'inventory.fbaSubtitle',
  overseas: 'inventory.overseasSubtitle',
  domestic: 'inventory.domesticSubtitle',
} as const

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchBalances(props.kind)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const totals = computed(() => ({
  onHand: rows.value.reduce((sum, row) => sum + row.onHand, 0),
  inTransit: rows.value.reduce((sum, row) => sum + row.inTransit, 0),
  unfulfillable: rows.value.reduce((sum, row) => sum + row.unfulfillable, 0),
}))

const columns = computed(() => [
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'internalSku', title: t('inventory.sku') },
  { key: 'title', title: t('inventory.name') },
  { key: 'onHand', title: t('inventory.onHand'), align: 'end' as const },
  { key: 'inTransit', title: t('inventory.inTransit'), align: 'end' as const },
  { key: 'unfulfillable', title: t('inventory.unfulfillable'), align: 'end' as const },
  { key: 'available', title: t('inventory.available'), align: 'end' as const },
])

const filters = computed(() => [{
  key: 'warehouseName',
  label: t('inventory.warehouse'),
  items: [...new Set(rows.value.map(item => item.warehouseName))].map(name => ({ title: name, value: name })),
}])
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      {{ t('inventory.syncLater') }}
    </VAlert>
    <ListPage
      :storage-key="storageKey"
      :title="t(titleKey[kind])"
      :subtitle="t(subtitleKey[kind])"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #widgets>
        <VRow class="mb-6">
          <VCol
            cols="12"
            md="4"
          >
            <KpiCard
              :title="t('inventory.onHand')"
              :value="formatInteger(totals.onHand)"
              icon="tabler-packages"
            />
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <KpiCard
              :title="t('inventory.inTransit')"
              :value="formatInteger(totals.inTransit)"
              icon="tabler-truck"
              color="info"
            />
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <KpiCard
              :title="t('inventory.unfulfillable')"
              :value="formatInteger(totals.unfulfillable)"
              icon="tabler-alert-triangle"
              color="warning"
            />
          </VCol>
        </VRow>
      </template>
    </ListPage>
  </div>
</template>
