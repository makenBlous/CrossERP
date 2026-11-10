<script setup lang="ts">
import { fetchLandedCosts } from '@/api/fin-cost'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { LandedCostVoucher } from '@/mocks/services/fin-cost'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<LandedCostVoucher[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchLandedCosts()
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
  { key: 'no', title: t('finance.financeCost.voucherNo') },
  { key: 'shipmentId', title: t('finance.financeCost.shipment') },
  { key: 'period', title: t('finance.period') },
  { key: 'basis', title: t('finance.financeCost.basis') },
  { key: 'poolAmount', title: t('finance.amount'), align: 'end' as const },
  { key: 'status', title: t('finance.status') },
  { key: 'submitterName', title: t('finance.financeCost.submitter') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('finance.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(value => ({ title: value, value })),
}])
</script>

<template>
  <VAlert
    type="info"
    variant="tonal"
    class="mb-4"
  >
    {{ t('finance.financeCost.demoNotice') }}
  </VAlert>
  <ListPage
    storage-key="finance-landed-costs"
    :title="t('finance.financeCost.landedCostsTitle')"
    :subtitle="t('finance.financeCost.landedCostsSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    :loading="loading"
    :error="error"
    @retry="load"
    @open="row => router.push(`/finance/landed-costs/${row.id}`)"
  >
    <template #item.basis>
      {{ t('finance.financeCost.chargeableWeight') }}
    </template>
    <template #item.poolAmount="{ item }">
      <MoneyText
        :amount="item.poolAmount"
        minor
        currency="CNY"
      />
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="voucher"
        :value="item.status === 'pending' ? 'pending' : item.status === 'posted' ? 'posted' : item.status"
      />
    </template>
  </ListPage>
</template>
