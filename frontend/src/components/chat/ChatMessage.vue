<script setup lang="ts">
import type { ChatDisplayMessage } from './types'
import ChatLog from '@/views/apps/chat/ChatLog.vue'

defineProps<{
  message: ChatDisplayMessage
  assistantName: string
  selfName: string
}>()
</script>

<template>
  <!-- 兼容旧引用：实际气泡渲染统一由已有 ChatLog 完成。 -->
  <ChatLog
    :messages="[message]"
    :contact-name="assistantName"
    :self-name="selfName"
  >
    <template #after="{ message: renderedMessage }">
      <slot :message="renderedMessage" />
    </template>
  </ChatLog>
</template>
