/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchClearing } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/pages/finance/_components/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchClearing>>>([])

onMounted(async () => { rows.value = await fetchClearing() })

const columns = [{ key: 'payout', title: '打款' }, { key: 'ar', title: '应收' }, { key: 'currency', title: '币种' }, { key: 'payoutAmount', title: '打款金额', align: 'end' as const }, { key: 'arAmount', title: '应收金额', align: 'end' as const }, { key: 'difference', title: '差额', align: 'end' as const }, { key: 'status', title: '状态' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-clearing"
    title="收付款核销"
    subtitle="服务层检查两侧金额相等后，提交审批才会生效。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  >
    <template #item.difference="{ item }">
      <VChip
        size="small"
        :color="item.difference === 0 ? 'success' : 'error'"
      >
        {{ item.difference }}
      </VChip>
    </template><template #actions>
      <VBtn
        prepend-icon="tabler-send"
        variant="tonal"
      >
        提交核销审批
      </VBtn>
    </template>
  </FinanceTablePage>
</template>

