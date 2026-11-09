<script setup lang="ts">
import { fetchAp, fetchApAging } from '@/api/finance'
import KpiCard from '@/components/KpiCard.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAp>>>([])
const aging = ref<Awaited<ReturnType<typeof fetchApAging>>>([])

onMounted(async () => {
  const result = await Promise.all([fetchAp(), fetchApAging()])
  rows.value = result[0]
  aging.value = result[1]
})

const agingLabels: Record<string, string> = { '0-30': '0-30 天', '31-60': '31-60 天', '61-90': '61-90 天', '90+': '90+ 天' }

const columns = [{ key: 'id', title: '应付编号' }, { key: 'supplier', title: '供应商' }, { key: 'amountDisplay', title: '金额', align: 'end' as const }, { key: 'currency', title: '币种' }, { key: 'bucket', title: '账龄' }, { key: 'status', title: '状态' }, { key: 'dueAt', title: '到期日' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-ap"
    title="应付账款"
    subtitle="供应商、货代未付款金额与账龄。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
    :filters="[{ key: 'supplier', label: '供应商', items: [...new Set(rows.map(row => ({ title: row.supplier, value: row.supplier })))] }, { key: 'status', label: '状态', items: [...new Set(rows.map(row => ({ title: row.status, value: row.status })))] }]"
    date-key="dueAt"
  ><template #widgets><VRow class="mb-6"><VCol v-for="bucket in aging" :key="bucket.key" cols="12" sm="6" lg="3"><KpiCard :title="agingLabels[bucket.key]" :value="String(bucket.count)" icon="tabler-calendar-stats" color="primary" /><div v-for="amount in bucket.amounts" :key="amount.currency" class="text-caption mt-1"><MoneyText :amount="amount.amount" :currency="amount.currency" minor /></div></VCol></VRow></template>
  ><template #item.amountDisplay="{ item }"><MoneyText :amount="Number(item.amount)" :currency="item.currency as any" minor /></template></FinanceTablePage>
</template>
