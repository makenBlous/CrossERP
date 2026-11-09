<script setup lang="ts">
import { fetchExceptions } from '@/api/orders'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { ExceptionRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const rows = ref<ExceptionRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchExceptions()
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
  { key: 'code', title: t('orders.reason') },
  { key: 'severity', title: t('orders.severity') },
  { key: 'storeName', title: t('common.store') },
  { key: 'refNo', title: t('orders.refNo') },
  { key: 'status', title: t('common.status') },
  { key: 'summary', title: t('orders.summary') },
  { key: 'amount', title: t('common.amount'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'code', label: t('orders.reason'), items: [...new Set(rows.value.map(item => item.code))].map(name => ({ title: name, value: name })) },
  { key: 'severity', label: t('orders.severity'), items: [...new Set(rows.value.map(item => item.severity))].map(name => ({ title: name, value: name })) },
  { key: 'status', label: t('common.status'), items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })) },
])

function openRow(row: ExceptionRow) {
  setSelected(row.orderId || row.id)
  router.push({ path: row.orderId ? `/orders/${row.orderId}` : '/finance/issues' })
}
</script>

<template>
  <ListPage
    storage-key="order-exceptions"
    :title="t('orders.exceptionsTitle')"
    :subtitle="t('orders.exceptionsSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    :loading="loading"
    :error="error"
    :batch-actions="[{ key: 'open', label: t('orders.openOrder') }]"
    @retry="load"
    @open="openRow"
    @batch="(_action, selected) => selected[0] && openRow(selected[0])"
  >
    <template #item.status="{ item }">
      <StatusChip
        domain="issue"
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
        v-if="item.orderId"
        size="small"
        variant="text"
        :to="{ path: `/orders/${item.orderId}` }"
      >
        {{ t('orders.openOrder') }}
      </VBtn>
      <VBtn
        size="small"
        variant="text"
        :to="{ path: '/finance/issues' }"
      >
        {{ t('issues.title') }}
      </VBtn>
    </template>
  </ListPage>
</template>
