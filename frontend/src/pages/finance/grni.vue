<script setup lang="ts">
import { fetchGrniBalances } from '@/api/fin-cost'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { GrniRow } from '@/mocks/services/fin-cost'
import { formatMoney } from '@/utils/format'
import { toDisplay } from '@/utils/money'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<GrniRow[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchGrniBalances()
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
  { key: 'receiptNo', title: t('finance.financeCost.receiptNo') },
  { key: 'supplier', title: t('finance.financeCost.supplier') },
  { key: 'receivedAt', title: t('finance.financeCost.receivedAt') },
  { key: 'estimatedAmount', title: t('finance.financeCost.estimated'), align: 'end' as const },
  { key: 'invoicedAmount', title: t('finance.financeCost.invoiced'), align: 'end' as const },
  { key: 'balanceAmount', title: t('finance.financeCost.balance'), align: 'end' as const },
  { key: 'offsetProgress', title: t('finance.financeCost.progress'), align: 'end' as const },
  { key: 'status', title: t('finance.status') },
  { key: 'nextAction', title: t('finance.financeCost.nextAction') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('finance.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(value => ({ title: value, value })),
}])

const openBalance = computed(() => rows.value.reduce((sum, row) => sum + row.balanceAmount, 0))
</script>

<template>
  <VAlert
    type="warning"
    variant="tonal"
    class="mb-4"
  >
    {{ t('finance.financeCost.grniNotice') }}
  </VAlert>
  <ListPage
    storage-key="finance-grni"
    :title="t('finance.financeCost.grniTitle')"
    :subtitle="t('finance.financeCost.grniSubtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    date-key="receivedAt"
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
            :title="t('finance.financeCost.openGrni')"
            :value="String(rows.filter(row => row.status !== 'cleared').length)"
            icon="tabler-receipt-tax"
            color="warning"
          />
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <KpiCard
            :title="t('finance.financeCost.openBalance')"
            :value="formatMoney(toDisplay(openBalance, 'CNY'), 'CNY')"
            icon="tabler-coins"
            color="primary"
          />
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <KpiCard
            :title="t('finance.financeCost.cleared')"
            :value="String(rows.filter(row => row.status === 'cleared').length)"
            icon="tabler-check"
            color="success"
          />
        </VCol>
      </VRow>
    </template>
    <template #item.estimatedAmount="{ item }">
      <MoneyText
        :amount="item.estimatedAmount"
        minor
        currency="CNY"
      />
    </template>
    <template #item.invoicedAmount="{ item }">
      <MoneyText
        :amount="item.invoicedAmount"
        minor
        currency="CNY"
      />
    </template>
    <template #item.balanceAmount="{ item }">
      <MoneyText
        :amount="item.balanceAmount"
        minor
        currency="CNY"
      />
    </template>
    <template #item.offsetProgress="{ item }">
      <VProgressLinear
        :model-value="item.offsetProgress"
        color="success"
        height="8"
        rounded
        class="mb-1"
      />
      <span class="text-caption">{{ item.offsetProgress }}%</span>
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="ap_item"
        :value="item.status === 'cleared' ? 'paid' : 'open'"
      />
    </template>
  </ListPage>
</template>
