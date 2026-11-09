<script setup lang="ts">
import { fetchGapAVouchers } from '@/api/gap-a'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { VoucherRow, VoucherStatus } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<VoucherRow[]>([])

onMounted(async () => {
  rows.value = (await fetchGapAVouchers()).map(item => ({
    id: item.id,
    no: item.no,
    period: item.period,
    status: item.status,
    debit: item.debit,
    credit: item.credit,
    currency: item.currency,
    summary: item.summary,
    submitter: '演示用户',
  }))
})

const columns = computed(() => [
  { key: 'no', title: t('vouchers.no') },
  { key: 'period', title: t('common.period') },
  { key: 'status', title: t('common.status') },
  { key: 'debit', title: t('vouchers.debit'), align: 'end' as const },
  { key: 'credit', title: t('vouchers.credit'), align: 'end' as const },
  { key: 'submitter', title: t('vouchers.submitter') },
  { key: 'summary', title: t('vouchers.summary') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: (['draft', 'pending', 'posted'] as VoucherStatus[]).map(status => ({
    title: t(`vouchers.${status}`),
    value: status,
  })),
}])
</script>

<template>
  <ListPage
    storage-key="finance-vouchers"
    :title="t('vouchers.title')"
    :subtitle="t('vouchers.subtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    @open="item => router.push(`/finance/vouchers/${item.id}`)"
  >
    <template #widgets>
      <VRow class="mb-6">
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="凭证总数"
            :value="String(rows.length)"
            icon="tabler-notebook"
          />
        </VCol>
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="待审批"
            :value="String(rows.filter(item => item.status === 'pending').length)"
            icon="tabler-clock"
            color="warning"
          />
        </VCol>
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="已批准"
            :value="String(rows.filter(item => item.status === 'approved' || item.status === 'posted').length)"
            icon="tabler-check"
            color="success"
          />
        </VCol>
      </VRow>
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="voucher"
        :value="item.status"
      />
    </template>
    <template #item.debit="{ item }">
      <MoneyText
        :amount="item.debit"
        minor
        currency="CNY"
      />
    </template>
    <template #item.credit="{ item }">
      <MoneyText
        :amount="item.credit"
        minor
        currency="CNY"
      />
      <VChip
        v-if="item.debit === item.credit"
        size="x-small"
        color="success"
        class="ms-2"
      >
        {{ t('vouchers.balanced') }}
      </VChip>
    </template>
  </ListPage>
</template>
