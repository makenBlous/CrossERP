<script setup lang="ts">
import { fetchTracking } from '@/api/logistics'
import ListPage from '@/components/biz/ListPage.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { TrackingRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const rows = ref<TrackingRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchTracking()
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
  { key: 'shipmentNo', title: t('logistics.search') },
  { key: 'occurredAt', title: t('orders.date') },
  { key: 'description', title: t('logistics.tracking') },
  { key: 'status', title: t('common.status') },
])

const filters = computed(() => [{
  key: 'shipmentNo',
  label: t('logistics.search'),
  items: [...new Set(rows.value.map(item => item.shipmentNo))].map(name => ({ title: name, value: name })),
}])

function openRow(row: TrackingRow) {
  setSelected(row.shipmentId)
  router.push({ path: `/logistics/shipments/${row.shipmentId}` })
}
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      {{ t('logistics.noMap') }}
    </VAlert>
    <ListPage
      storage-key="logistics-tracking"
      :title="t('logistics.trackingTitle')"
      :subtitle="t('logistics.trackingSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="occurredAt"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
      <template #item.status="{ item }">
        <StatusChip
          v-if="item.status"
          domain="shipment"
          :value="item.status"
        />
      </template>
    </ListPage>
  </div>
</template>
