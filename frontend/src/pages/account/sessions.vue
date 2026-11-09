<script setup lang="ts">
import { fetchSessions } from '@/api/account'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchSessions()
})

const columns = [{ key: 'device', title: '设备' }, { key: 'location', title: '位置' }, { key: 'ip', title: 'IP' }, { key: 'lastSeenAt', title: '最近活动' }, { key: 'current', title: '当前会话' }]
</script>

<template>
  <ModuleTable
    storage-key="account-sessions"
    title="我的会话"
    subtitle="查看最近设备并识别异常登录。"
    :rows="rows"
    :columns="columns"
  >
    <template #cell.current="{ item }">
      <VChip
        size="small"
        :color="item.current ? 'success' : 'secondary'"
        variant="tonal"
      >
        {{ item.current ? '当前' : '其他设备' }}
      </VChip>
    </template>
  </ModuleTable>
</template>
