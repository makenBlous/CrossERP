<script setup lang="ts">
import { fetchAr } from '@/api/finance'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAr>>>([])

onMounted(async () => {
  rows.value = await fetchAr()
})

const columns = [{ key: 'id', title: '应收编号' }, { key: 'storeName', title: '店铺' }, { key: 'amountDisplay', title: '金额', align: 'end' as const }, { key: 'currency', title: '币种' }, { key: 'bucket', title: '账龄' }, { key: 'status', title: '状态' }, { key: 'dueAt', title: '到期日' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-ar"
    title="应收账款"
    subtitle="平台未打款金额与账龄。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
    :filters="[{ key: 'storeName', label: '店铺', items: [...new Set(rows.map(row => ({ title: row.storeName, value: row.storeName })))] }, { key: 'status', label: '状态', items: [...new Set(rows.map(row => ({ title: row.status, value: row.status })))] }]"
    date-key="dueAt"
  ><template #item.amountDisplay="{ item }"><MoneyText :amount="Number(item.amount)" :currency="item.currency as any" minor /></template></FinanceTablePage>
</template>
