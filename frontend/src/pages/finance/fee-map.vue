/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { confirmFee, fetchFeeMap } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/pages/finance/_components/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchFeeMap>>>([])

onMounted(async () => { rows.value = await fetchFeeMap() })

const columns = [{ key: 'platform', title: '平台' }, { key: 'description', title: '费用描述' }, { key: 'category', title: '分类' }, { key: 'suggestion', title: 'AI 建议' }, { key: 'status', title: '状态' }, { key: 'actions', title: '操作' }]
async function confirm(row: FinanceRow) { rows.value = await confirmFee(String(row.id), String(row.suggestion)) }
</script>

<template>
  <FinanceTablePage
    storage-key="finance-fee-map"
    title="费用分类映射"
    subtitle="AI 只能给建议，人工确认后才会生效。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  >
    <template #item.status="{ item }">
      <VChip
        size="small"
        :color="item.status === 'confirmed' ? 'success' : 'warning'"
      >
        {{ item.status }}
      </VChip>
    </template><template #item.actions="{ item }">
      <VBtn
        v-if="item.status === 'unmapped'"
        size="small"
        variant="tonal"
        @click="confirm(item)"
      >
        确认建议
      </VBtn>
    </template>
  </FinanceTablePage>
</template>

