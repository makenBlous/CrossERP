<script setup lang="ts">
import { fetchCash } from '@/api/finance'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchCash>>>([])

onMounted(async () => {
  rows.value = await fetchCash()
})

const columns = [{ key: 'date', title: '日期' }, { key: 'account', title: '资金账户' }, { key: 'direction', title: '方向' }, { key: 'amount', title: '金额', align: 'end' as const }, { key: 'currency', title: '币种' }, { key: 'source', title: '来源' }, { key: 'status', title: '打款核对' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-cash"
    title="资金流水"
    subtitle="平台和银行资金账户的已导入流水。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
    :filters="[{ key: 'direction', label: '方向', items: [{ title: '流入', value: 'in' }] }, { key: 'account', label: '资金账户', items: [...new Set(rows.map(row => ({ title: row.account, value: row.account })))] }]"
    date-key="date"
  ><template #item.amount="{ item }"><MoneyText :amount="Number(item.amount)" :currency="item.currency as any" minor /></template></FinanceTablePage>
</template>
