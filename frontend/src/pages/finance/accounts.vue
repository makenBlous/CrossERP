<script setup lang="ts">
import { fetchAccounts } from '@/api/finance'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAccounts>>>([])

onMounted(async () => {
  rows.value = await fetchAccounts()
})

const columns = [{ key: 'code', title: '科目编码' }, { key: 'name', title: '科目名称' }, { key: 'direction', title: '方向' }, { key: 'active', title: '启用' }, { key: 'review', title: '核实' }]
</script>

<template>
  <FinanceTablePage
    storage-key="finance-accounts"
    title="科目表"
    subtitle="默认科目标注待会计核实。"
    :rows="rows as unknown as FinanceRow[]"
    :columns="columns"
  >
    <template #item.review="{ item }">
      <VChip
        v-if="item.review"
        size="small"
        color="warning"
      >
        待会计核实
      </VChip><span v-else>—</span>
    </template>
  </FinanceTablePage>
</template>
