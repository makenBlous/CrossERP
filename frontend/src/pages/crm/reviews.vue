<script setup lang="ts">
import { fetchCrmReviews } from '@/api/crm'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchCrmReviews()
})

const columns = [{ key: 'author', title: '评价人' }, { key: 'source', title: '来源' }, { key: 'rating', title: '评分' }, { key: 'title', title: '标题' }, { key: 'sku', title: 'SKU' }, { key: 'status', title: '状态' }]
</script>

<template>
  <ModuleTable
    storage-key="crm-reviews"
    title="评价"
    subtitle="汇总独立站或已同步的评价。"
    :rows="rows"
    :columns="columns"
  >
    <template #cell.rating="{ item }">
      <span class="text-warning">{{ '★'.repeat(Number(item.rating)) }}</span>
    </template><template #cell.status="{ item }">
      <VChip
        size="small"
        :color="item.status === 'published' ? 'success' : 'warning'"
        variant="tonal"
      >
        {{ item.status === 'published' ? '已发布' : '待处理' }}
      </VChip>
    </template>
  </ModuleTable>
</template>
