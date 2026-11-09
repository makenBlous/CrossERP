<script setup lang="ts">
import { fetchCrmLeads } from '@/api/crm'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const router = useRouter()

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

const stageLabel: Record<string, string> = { new: '新线索', qualified: '已确认需求', proposal: '已报价', converted: '已转化' }

onMounted(async () => {
  rows.value = (await fetchCrmLeads()).map(item => ({ ...item, stageLabel: stageLabel[item.stage] }))
})

const columns = computed(() => [{ key: 'name', title: '联系人' }, { key: 'company', title: '公司' }, { key: 'source', title: '来源' }, { key: 'owner', title: '负责人' }, { key: 'stageLabel', title: '阶段' }, { key: 'createdAt', title: '创建日期' }])
</script>

<template>
  <ModuleTable
    storage-key="crm-leads"
    title="线索"
    subtitle="记录尚未成交的潜在客户。"
    :rows="rows"
    :columns="columns"
    @open="router.push(`/crm/leads/${$event.id}`)"
  >
    <template #cell.stageLabel="{ item }">
      <VChip
        size="small"
        color="primary"
        variant="tonal"
      >
        {{ item.stageLabel }}
      </VChip>
    </template>
  </ModuleTable>
</template>
