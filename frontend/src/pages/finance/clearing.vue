/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchClearing, submitClearingApproval } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchClearing>>>([])

onMounted(async () => { rows.value = await fetchClearing() })

const columns = [{ key: 'payout', title: '打款' }, { key: 'ar', title: '应收' }, { key: 'currency', title: '币种' }, { key: 'payoutAmount', title: '打款金额', align: 'end' as const }, { key: 'arAmount', title: '应收金额', align: 'end' as const }, { key: 'difference', title: '差额', align: 'end' as const }, { key: 'status', title: '状态' }]
const submitted = ref(false)
async function submit() {
  await submitClearingApproval()
  submitted.value = true
}
</script>

<template>
  <div>
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
    <VBtn
      class="mt-4"
      prepend-icon="tabler-send"
      variant="tonal"
      @click="submit"
    >
      提交核销审批
    </VBtn>
    <VAlert
      v-if="submitted"
      type="success"
      variant="tonal"
      class="mt-4"
    >
      核销申请已进入审批队列。
    </VAlert>
  </div>
</template>
