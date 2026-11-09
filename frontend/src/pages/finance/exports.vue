/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchExports } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchExports>>>([])

onMounted(async () => { rows.value = await fetchExports() })

const columns = [{ key: 'fileName', title: '文件' }, { key: 'target', title: '目标' }, { key: 'approvalId', title: '审批' }, { key: 'sha256', title: 'SHA-256' }, { key: 'createdAt', title: '生成时间' }, { key: 'status', title: '状态' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-exports"
    title="导出产物"
    subtitle="只有已批准的审批才会产生导出文件。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  >
    <template #item.status="{ item }">
      <VChip
        color="success"
        size="small"
      >
        {{ item.status }}
      </VChip>
    </template><template #actions>
      <VAlert
        type="info"
        variant="tonal"
        density="compact"
        class="mb-0"
      >
        演示文件由审批通过后生成。
      </VAlert>
    </template>
  </FinanceTablePage>
</template>
