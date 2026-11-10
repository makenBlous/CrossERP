<script setup lang="ts">
import { fetchNotifications, updateNotification } from '@/api/admin'
import ListPage from '@/components/biz/ListPage.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

const error = ref('')
const message = ref('')

onMounted(async () => {
  rows.value = await fetchNotifications()
})

const columns = [{ key: 'channel', title: '渠道' }, { key: 'event', title: '事件' }, { key: 'target', title: '目标' }, { key: 'enabled', title: '状态' }]

async function saveRule(item: { id: string; enabled?: unknown }, value: unknown) {
  error.value = ''
  try {
    const saved = await updateNotification(item.id, Boolean(value))

    item.enabled = saved.enabled
    message.value = '通知规则已保存，并写入操作审计。'
  }
  catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  }
}
</script>

<template>
  <ListPage
    storage-key="admin-notifications"
    title="通知"
    subtitle="通知开关和安全的配置引用。"
    :items="rows"
    :columns="columns"
  >
    <template #widgets>
      <VAlert
        v-if="message"
        type="success"
        variant="tonal"
        class="mb-4"
      >
        {{ message }}
      </VAlert>
      <VAlert
        v-if="error"
        type="error"
        variant="tonal"
        class="mb-4"
      >
        {{ error }}
      </VAlert>
    </template>
    <template #item.enabled="{ item }">
      <VSwitch
        v-model="item.enabled"
        color="primary"
        hide-details
        @update:model-value="saveRule(item, $event)"
      />
    </template>
  </ListPage>
</template>
