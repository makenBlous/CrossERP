/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchSubmittedApprovals } from '@/api/approvals'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchSubmittedApprovals>>>([])

onMounted(async () => { rows.value = await fetchSubmittedApprovals() })

const columns = [{ key: 'title', title: '审批事项' }, { key: 'type', title: '类型' }, { key: 'submittedAt', title: '提交时间' }, { key: 'amount', title: '金额' }, { key: 'status', title: '状态' }]
</script>

<template>
  <FinanceTablePage
    storage-key="approvals-submitted"
    title="我提交的"
    subtitle="查看自己提交的凭证、建议和核销审批。"
    detail-base="/approvals"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  >
    <template #item.status="{ item }">
      <StatusChip
        domain="approval"
        :value="String(item.status)"
      />
    </template>
  </FinanceTablePage>
</template>
