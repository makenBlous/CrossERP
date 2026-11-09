<script setup lang="ts">
import { fetchAdCampaigns } from '@/api/ads'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAdCampaigns>>>([])

onMounted(async () => {
  rows.value = await fetchAdCampaigns()
})

const columns = [{ key: 'name', title: '活动' }, { key: 'storeName', title: '店铺' }, { key: 'status', title: '状态' }, { key: 'spendDisplay', title: '花费', align: 'end' as const }, { key: 'currency', title: '币种' }]
</script>

<template>
  <FinanceTablePage
    storage-key="ads-campaigns"
    title="广告活动"
    subtitle="按平台查看活动状态和花费。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
    :filters="[{ key: 'platform', label: '平台', items: [...new Set(rows.map(row => ({ title: row.platform, value: row.platform })))] }, { key: 'storeName', label: '店铺', items: [...new Set(rows.map(row => ({ title: row.storeName, value: row.storeName })))] }, { key: 'status', label: '状态', items: [...new Set(rows.map(row => ({ title: row.status, value: row.status })))] }]"
  ><template #item.spendDisplay="{ item }"><MoneyText :amount="Number(item.spend)" :currency="item.currency as any" minor /></template></FinanceTablePage>
</template>
