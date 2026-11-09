/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchIssues } from '@/api/finance'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { IssueCode, IssueRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<IssueRow[]>([])

const codes: IssueCode[] = [
  'DUPLICATE_ROW',
  'UNKNOWN_FEE_TYPE',
  'SETTLEMENT_UNBALANCED',
  'AMOUNT_MISMATCH',
]

onMounted(async () => {
  rows.value = await fetchIssues()
})

const columns = computed(() => [
  { key: 'code', title: t('issues.code') },
  { key: 'severity', title: t('issues.severity') },
  { key: 'storeName', title: t('common.store') },
  { key: 'refNo', title: t('issues.refNo') },
  { key: 'amount', title: t('common.amount'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'summary', title: t('issues.summary') },
])

function severityLabel(value: IssueRow['severity']) {
  if (value === 'high')
    return t('issues.high')
  if (value === 'medium')
    return t('issues.medium')

  return t('issues.low')
}

function severityColor(value: IssueRow['severity']) {
  if (value === 'high')
    return 'error'
  if (value === 'medium')
    return 'warning'

  return 'info'
}

const filters = computed(() => [
  {
    key: 'code',
    label: t('issues.code'),
    items: codes.map(code => ({ title: code, value: code })),
  },
  {
    key: 'severity',
    label: t('issues.severity'),
    items: [
      { title: t('issues.high'), value: 'high' },
      { title: t('issues.medium'), value: 'medium' },
      { title: t('issues.low'), value: 'low' },
    ],
  },
])
</script>

<template>
  <ListPage
    storage-key="finance-issues"
    :title="t('issues.title')"
    :subtitle="t('issues.subtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    @open="item => router.push(`/finance/issues/${item.id}`)"
  >
    <template #item.severity="{ item }">
      <VChip
        size="small"
        :color="severityColor(item.severity)"
      >
        {{ severityLabel(item.severity) }}
      </VChip>
    </template>
    <template #item.amount="{ item }">
      <MoneyText
        :amount="item.amount"
        :currency="item.currency"
      />
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="issue"
        :value="item.status"
      />
    </template>
  </ListPage>
</template>

