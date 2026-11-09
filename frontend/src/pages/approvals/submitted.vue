<script setup lang="ts">
import { fetchSubmittedApprovals } from '@/api/approvals'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { CurrencyCode } from '@/types/domain'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchSubmittedApprovals>>>([])

onMounted(async () => {
  rows.value = await fetchSubmittedApprovals()
})

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
    <template #item.amount="{ item }">
      <MoneyText
        :amount="Number(item.amount)"
        :currency="String(item.currency) as CurrencyCode"
        minor
      />
    </template>
  </FinanceTablePage>
</template>
