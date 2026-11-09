<script setup lang="ts">
import { fetchInboxNotifications, markInboxNotificationRead } from '@/api/gap-e'
import ListPage from '@/components/biz/ListPage.vue'
import type { InboxNotification } from '@/types/gap-e'

const router = useRouter()
const rows = ref<InboxNotification[]>([])
const error = ref('')
const message = ref('')

async function load() {
  try {
    rows.value = await fetchInboxNotifications()
  }
  catch (e) {
    error.value = e instanceof Error ? e.message : '消息加载失败'
  }
}

async function openNotification(item: InboxNotification) {
  try {
    if (!item.isRead) {
      const updated = await markInboxNotificationRead(item.id)

      item.isRead = updated.isRead
      message.value = '消息已读，操作已写入审计。'
    }
    if (item.href)
      await router.push(item.href)
  }
  catch (e) {
    error.value = e instanceof Error ? e.message : '消息操作失败'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      到期提醒和审核待办由 mock 服务写入站内消息中心；当前批次为模拟推送，真实渠道待后端接入。
    </VAlert>
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
    <ListPage
      storage-key="notifications-inbox"
      title="消息中心"
      subtitle="审核待办、到期提醒和系统通知。"
      :items="rows"
      :columns="[{ key: 'title', title: '消息' }, { key: 'detail', title: '详情' }, { key: 'type', title: '类型' }, { key: 'at', title: '时间' }, { key: 'isRead', title: '状态' }]"
      @open="openNotification"
    >
      <template #item.title="{ item }">
        <span :class="{ 'font-weight-bold': !item.isRead }">{{ item.title }}</span>
      </template>
      <template #item.isRead="{ item }">
        <VChip
          size="small"
          :color="item.isRead ? 'default' : 'primary'"
          variant="tonal"
        >
          {{ item.isRead ? '已读' : '未读' }}
        </VChip>
      </template>
    </ListPage>
  </div>
</template>
