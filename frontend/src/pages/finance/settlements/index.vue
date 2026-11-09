/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchSettlements } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchSettlements>>>([])

onMounted(async () => { rows.value = await fetchSettlements() })

const columns = [{ key: 'externalId', title: '结算编号' }, { key: 'storeName', title: '店铺' }, { key: 'platform', title: '平台' }, { key: 'periodStart', title: '开始' }, { key: 'periodEnd', title: '结束' }, { key: 'totalDisplay', title: '总额', align: 'end' as const }, { key: 'matched', title: '已匹配', align: 'end' as const }, { key: 'status', title: '状态' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-settlements"
    title="结算与打款"
    subtitle="Amazon 结算、Shopify 打款和 TikTok 结算。"
    detail-base="/finance/settlements"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>
