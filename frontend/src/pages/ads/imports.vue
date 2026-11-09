<script setup lang="ts">
import { fetchAdImports, uploadAdImport } from '@/api/ads'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'
import FinanceUpload from '@/views/finance/FinanceUpload.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAdImports>>>([])

onMounted(async () => {
  rows.value = await fetchAdImports()
})

const columns = [{ key: 'fileName', title: '文件' }, { key: 'platform', title: '平台' }, { key: 'rows', title: '行数' }, { key: 'spendDisplay', title: '花费' }, { key: 'status', title: '状态' }, { key: 'importedAt', title: '导入时间' }]
async function addBatch(fileName: string) {
  const row = await uploadAdImport(fileName)

  rows.value = [row, ...rows.value]
}
</script>

<template>
  <FinanceUpload
    title="广告花费导入"
    subtitle="模拟上传后解析广告日报，花费由服务层进入活动与利润分摊。"
    @uploaded="addBatch"
  >
    <FinanceTablePage
      storage-key="ads-imports"
      title="导入批次"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    >
      <template #item.spendDisplay="{ item }">
        <MoneyText
          :amount="Number(item.spend)"
          currency="USD"
          minor
        />
      </template>
    </FinanceTablePage>
  </FinanceUpload>
</template>
