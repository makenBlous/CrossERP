<script setup lang="ts">
import { fetchNotifications } from '@/api/admin'
import ListPage from '@/components/biz/ListPage.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchNotifications()
})

const columns = [{ key: 'channel', title: '渠道' }, { key: 'event', title: '事件' }, { key: 'target', title: '目标' }, { key: 'enabled', title: '状态' }]
</script>

<template>
  <ListPage
    storage-key="admin-notifications"
    title="通知"
    subtitle="通知开关和安全的配置引用。"
    :items="rows"
    :columns="columns"
  >
    <template #item.enabled="{ item }">
      <VSwitch
        v-model="item.enabled"
        color="primary"
        hide-details
      />
    </template>
  </ListPage>
</template>
