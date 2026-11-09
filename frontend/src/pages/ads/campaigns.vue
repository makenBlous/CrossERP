/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAdCampaigns } from '@/api/ads'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAdCampaigns>>>([])

onMounted(async () => { rows.value = await fetchAdCampaigns() })

const columns = [{ key: 'name', title: '活动' }, { key: 'storeName', title: '店铺' }, { key: 'status', title: '状态' }, { key: 'spendDisplay', title: '花费', align: 'end' as const }, { key: 'currency', title: '币种' }]
</script>

<template>
  <FinanceTablePage
    storage-key="ads-campaigns"
    title="广告活动"
    subtitle="按平台查看活动状态和花费。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>
