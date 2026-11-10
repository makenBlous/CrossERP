<script setup lang="ts">
import { fetchInboxNotifications } from '@/api/gap-e'
import GapCPage from '@/views/gap-c/GapCPage.vue'
import type { InboxNotification } from '@/types/gap-e'

const inbox = ref<InboxNotification[]>([])
const inboxError = ref('')

onMounted(async () => {
  try {
    inbox.value = await fetchInboxNotifications()
  }
  catch (error) {
    inboxError.value = error instanceof Error ? error.message : '收件箱加载失败'
  }
})
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-center gap-3 mb-4">
      <div class="text-body-2">
        到期提醒与审核待办来自收件箱同一数据源。
      </div>
      <VBtn
        to="/notifications/inbox"
        variant="tonal"
        prepend-icon="tabler-inbox"
      >
        打开消息收件箱
      </VBtn>
    </div>
    <VAlert
      v-if="inboxError"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ inboxError }}
    </VAlert>
    <VList
      v-if="inbox.length"
      class="mb-6"
      lines="two"
      border
      rounded
    >
      <VListItem
        v-for="item in inbox"
        :key="item.id"
        :title="item.title"
        :subtitle="item.detail"
        :to="item.href"
      />
    </VList>
    <GapCPage page-id="N01" />
  </div>
</template>
