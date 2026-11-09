/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchFxRates } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/pages/finance/_components/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchFxRates>>>([])

onMounted(async () => { rows.value = await fetchFxRates() })

const columns = [{ key: 'period', title: '期间' }, { key: 'fromCcy', title: '源币种' }, { key: 'toCcy', title: '目标币种' }, { key: 'rate', title: '汇率' }, { key: 'source', title: '来源' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-fx"
    title="汇率表"
    subtitle="用户提供的月汇率；不调用实时汇率。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>

