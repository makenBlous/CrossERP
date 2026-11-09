/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchImports } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'
import FinanceUpload from '@/views/finance/FinanceUpload.vue'
import type { ImportBatchRow } from '@/mocks/services/finance'

const rows = ref<ImportBatchRow[]>([])

onMounted(async () => { rows.value = await fetchImports() })

const columns = [{ key: 'fileName', title: '文件' }, { key: 'connector', title: '连接器' }, { key: 'status', title: '状态' }, { key: 'rows', title: '行数', align: 'end' as const }, { key: 'errors', title: '错误', align: 'end' as const }, { key: 'importedAt', title: '导入时间' }]
</script>

<template>
  <FinanceUpload
    title="文件导入"
    subtitle="上传结算、打款、订单、成本和汇率文件。"
  >
    <FinanceTablePage
      storage-key="finance-imports"
      title="最近批次"
      subtitle="失败批次保留原因，原始行可追溯。"
      detail-base="/finance/imports"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    />
  </FinanceUpload>
</template>
