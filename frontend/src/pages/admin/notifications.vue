<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchNotifications } from '@/api/admin'; import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string; [key: string]: unknown }>>([])

onMounted(async () => { rows.value = await fetchNotifications() })

const columns = [{ key: 'channel', title: '渠道' }, { key: 'event', title: '事件' }, { key: 'target', title: '目标' }, { key: 'enabled', title: '状态' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-notifications"
    title="通知"
    subtitle="通知开关和安全的配置引用。"
    :rows="rows"
    :columns="columns"
  >
    <template #cell.enabled="{ item }">
      <VSwitch
        v-model="item.enabled"
        color="primary"
        hide-details
      />
    </template>
  </ModuleTable>
</template>
