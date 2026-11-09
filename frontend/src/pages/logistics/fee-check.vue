<script setup lang="ts">
import { fetchFreightChecks, submitFreightCheck } from '@/api/logistics'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { FreightCheckRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const rows = ref<FreightCheckRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchFreightChecks()
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
  { key: 'shipmentNo', title: t('inventory.docNo') },
  { key: 'billAmount', title: t('logistics.bill'), align: 'end' as const },
  { key: 'estimateAmount', title: t('logistics.estimate'), align: 'end' as const },
  { key: 'variance', title: t('logistics.variance'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

function openRow(row: FreightCheckRow) {
  setSelected(row.shipmentId)
  router.push({ path: `/logistics/shipments/${row.shipmentId}` })
}

async function submit(row: FreightCheckRow) {
  message.value = ''
  try {
    await submitFreightCheck(row.id)
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
      storage-key="logistics-fee-check"
      :title="t('logistics.feeTitle')"
      :subtitle="t('logistics.feeSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
      <template #item.billAmount="{ item }">
        <MoneyText
          :amount="item.billAmount"
          :currency="item.currency"
        />
      </template>
      <template #item.estimateAmount="{ item }">
        <MoneyText
          :amount="item.estimateAmount"
          :currency="item.currency"
        />
      </template>
      <template #item.variance="{ item }">
        <MoneyText
          :amount="item.variance"
          :currency="item.currency"
        />
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="freight"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <PermissionGate action="suggest">
          <VBtn
            v-if="item.status === 'variance'"
            size="small"
            variant="text"
            @click="submit(item)"
          >
            {{ t('logistics.submitCheck') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
  </div>
</template>
