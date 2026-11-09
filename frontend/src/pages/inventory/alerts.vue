<script setup lang="ts">
import { fetchAlerts } from '@/api/inventory'
import { submitAgentSuggestion } from '@/api/workflows'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { AlertRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<AlertRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchAlerts()
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
  { key: 'internalSku', title: t('inventory.sku') },
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'kind', title: t('inventory.alert') },
  { key: 'onHand', title: t('inventory.onHand'), align: 'end' as const },
  { key: 'threshold', title: t('inventory.threshold'), align: 'end' as const },
  { key: 'triggeredAt', title: t('orders.date') },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'kind',
  label: t('inventory.alert'),
  items: [...new Set(rows.value.map(item => item.kind))].map(name => ({ title: name, value: name })),
}])

async function suggest(row: AlertRow) {
  message.value = ''
  try {
    await submitAgentSuggestion({
      title: `${t('inventory.suggestBuy')} ${row.internalSku}`,
      summary: `${row.warehouseName} ${row.kind}，${t('inventory.onHand')} ${row.onHand}，${t('inventory.threshold')} ${row.threshold}。只创建待审批建议，不自动下单。`,
      amount: '0.0000',
      currency: 'CNY',
      storeId: null,
      targetType: 'stock_alert',
      targetId: row.id,
    })
    message.value = t('inventory.suggestSent')
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="inventory-alerts"
      :title="t('inventory.alertsTitle')"
      :subtitle="t('inventory.alertsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="triggeredAt"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #item.kind="{ item }">
        <StatusChip
          domain="stock_alert"
          :value="item.kind === 'stockout' ? 'stockout' : 'low'"
        />
      </template>
      <template #item.actions="{ item }">
        <PermissionGate action="suggest">
          <VBtn
            size="small"
            variant="text"
            @click="suggest(item)"
          >
            {{ t('inventory.suggestBuy') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
  </div>
</template>
