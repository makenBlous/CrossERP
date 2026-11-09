<script setup lang="ts">
import { fetchSettings } from '@/api/admin'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchSettings()
})

const columns = [{ key: 'label', title: '参数' }, { key: 'key', title: '键' }, { key: 'value', title: '当前值' }, { key: 'description', title: '说明' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-settings"
    title="系统参数"
    subtitle="全局开关和默认展示设置。"
    :rows="rows"
    :columns="columns"
  >
    <template #cell.value="{ item }">
      <VSwitch
        v-if="typeof item.value === 'boolean'"
        v-model="item.value"
        hide-details
        color="primary"
      /><VChip
        v-else
        size="small"
        variant="tonal"
      >
        {{ item.value }}
      </VChip>
    </template>
  </ModuleTable>
</template>
