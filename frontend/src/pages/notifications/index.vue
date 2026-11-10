<script setup lang="ts">
import InboxPage from './inbox.vue'
import { fetchInboxNotifications, markInboxNotificationRead } from '@/api/gap-e'
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
    <InboxPage
      :load-notifications="fetchInboxNotifications"
      :mark-read="markInboxNotificationRead"
    />
  </div>
</template>
