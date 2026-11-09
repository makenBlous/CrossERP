/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAp } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAp>>>([])

onMounted(async () => { rows.value = await fetchAp() })

const columns = [{ key: 'id', title: '应付编号' }, { key: 'supplier', title: '供应商' }, { key: 'amountDisplay', title: '金额', align: 'end' as const }, { key: 'currency', title: '币种' }, { key: 'bucket', title: '账龄' }, { key: 'status', title: '状态' }, { key: 'dueAt', title: '到期日' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-ap"
    title="应付账款"
    subtitle="供应商、货代未付款金额与账龄。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>
