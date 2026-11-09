/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchColumnMaps } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchColumnMaps>>>([])

onMounted(async () => { rows.value = await fetchColumnMaps() })

const columns = [{ key: 'connector', title: '连接器' }, { key: 'name', title: '模板' }, { key: 'fields', title: '标准字段', align: 'end' as const }, { key: 'status', title: '状态' }, { key: 'updatedAt', title: '更新时间' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-column-maps"
    title="列映射模板"
    subtitle="领星、赛狐导出列对应标准字段。建议必须人工确认。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  />
</template>
