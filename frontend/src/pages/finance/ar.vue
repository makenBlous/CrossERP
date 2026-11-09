/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAr } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAr>>>([])

onMounted(async () => { rows.value = await fetchAr() })

const columns = [{ key: 'id', title: '应收编号' }, { key: 'storeName', title: '店铺' }, { key: 'amountDisplay', title: '金额', align: 'end' as const }, { key: 'currency', title: '币种' }, { key: 'bucket', title: '账龄' }, { key: 'status', title: '状态' }, { key: 'dueAt', title: '到期日' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-ar"
    title="应收账款"
    subtitle="平台未打款金额与账龄。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>
