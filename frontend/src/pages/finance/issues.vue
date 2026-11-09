<script setup lang="ts">
import { fetchIssues } from '@/api/finance'
import type { IssueCode, IssueRow } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<IssueRow[]>([])
const code = ref<IssueCode | 'all'>('all')

const codes: Array<IssueCode | 'all'> = [
  'all',
  'DUPLICATE_ROW',
  'UNKNOWN_FEE_TYPE',
  'SETTLEMENT_UNBALANCED',
  'AMOUNT_MISMATCH',
]

onMounted(async () => {
  rows.value = await fetchIssues()
})

const filtered = computed(() => rows.value.filter(item => code.value === 'all' || item.code === code.value))

const headers = computed(() => [
  { title: t('issues.code'), key: 'code' },
  { title: t('issues.severity'), key: 'severity' },
  { title: t('common.store'), key: 'storeName' },
  { title: t('issues.refNo'), key: 'refNo' },
  { title: t('common.amount'), key: 'amount', align: 'end' as const },
  { title: t('common.status'), key: 'status' },
  { title: t('issues.summary'), key: 'summary' },
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
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('issues.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('issues.subtitle') }}
      </p>
    </div>
    <div class="d-flex flex-wrap gap-2 mb-4">
      <VChip
        v-for="item in codes"
        :key="item"
        :color="code === item ? 'primary' : undefined"
        :variant="code === item ? 'flat' : 'outlined'"
        @click="code = item"
      >
        {{ item === 'all' ? t('issues.all') : item }}
      </VChip>
    </div>
    <VCard>
      <VDataTable
        :headers="headers"
        :items="filtered"
        :items-per-page="10"
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
          {{ formatMoney(item.amount, item.currency) }}
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
