<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchDictionaries } from '@/api/admin'; import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string; [key: string]: unknown }>>([])

onMounted(async () => { rows.value = await fetchDictionaries() })

const columns = [{ key: 'group', title: '分组' }, { key: 'code', title: '编码' }, { key: 'label', title: '名称' }, { key: 'active', title: '启用' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-dicts"
    title="数据字典"
    subtitle="原因码、工单状态和来源等可配置项。"
    :rows="rows"
    :columns="columns"
  >
    <template #cell.active="{ item }">
      <VChip
        size="small"
        :color="item.active ? 'success' : 'secondary'"
        variant="tonal"
      >
        {{ item.active ? '启用' : '停用' }}
      </VChip>
    </template>
  </ModuleTable>
</template>
