/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAdImports } from '@/api/ads'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'
import FinanceUpload from '@/views/finance/FinanceUpload.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAdImports>>>([])

onMounted(async () => { rows.value = await fetchAdImports() })

const columns = [{ key: 'fileName', title: '文件' }, { key: 'platform', title: '平台' }, { key: 'rows', title: '行数' }, { key: 'spend', title: '花费' }, { key: 'status', title: '状态' }, { key: 'importedAt', title: '导入时间' }]
</script>

<template>
  <FinanceUpload
    title="广告花费导入"
    subtitle="模拟上传后解析广告日报，花费由服务层进入活动与利润分摊。"
  >
    <FinanceTablePage
      storage-key="ads-imports"
      title="导入批次"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    />
  </FinanceUpload>
</template>
