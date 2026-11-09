<script setup lang="ts">
import { fetchVouchers } from '@/api/finance'
import type { VoucherRow, VoucherStatus } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<VoucherRow[]>([])
const status = ref<VoucherStatus | 'all'>('all')

onMounted(async () => {
  rows.value = await fetchVouchers()
})

const tabs: Array<VoucherStatus | 'all'> = ['all', 'draft', 'pending', 'posted']

const filtered = computed(() => rows.value.filter(item => status.value === 'all' || item.status === status.value))

const headers = computed(() => [
  { title: t('vouchers.no'), key: 'no' },
  { title: t('common.period'), key: 'period' },
  { title: t('common.status'), key: 'status' },
  { title: t('vouchers.debit'), key: 'debit', align: 'end' as const },
  { title: t('vouchers.credit'), key: 'credit', align: 'end' as const },
  { title: t('vouchers.submitter'), key: 'submitter' },
  { title: t('vouchers.summary'), key: 'summary' },
])

function statusLabel(value: VoucherStatus) {
  return t(`vouchers.${value}`)
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('vouchers.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('vouchers.subtitle') }}
      </p>
    </div>
    <VTabs
      v-model="status"
      class="mb-4"
    >
      <VTab
        v-for="item in tabs"
        :key="item"
        :value="item"
      >
        {{ item === 'all' ? t('vouchers.all') : t(`vouchers.${item}`) }}
      </VTab>
    </VTabs>
    <VCard>
      <VDataTable
        :headers="headers"
        :items="filtered"
        :items-per-page="10"
      >
        <template #item.status="{ item }">
          <VChip size="small">
            {{ statusLabel(item.status) }}
          </VChip>
        </template>
        <template #item.debit="{ item }">
          {{ formatMoney(item.debit, item.currency) }}
        </template>
        <template #item.credit="{ item }">
          <span>{{ formatMoney(item.credit, item.currency) }}</span>
          <VChip
            v-if="item.debit === item.credit"
            size="x-small"
            color="success"
            class="ms-2"
          >
            {{ t('vouchers.balanced') }}
          </VChip>
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
