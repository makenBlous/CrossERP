<script setup lang="ts">
import ChatMessageForm from '@/views/apps/chat/ChatMessageForm.vue'

withDefaults(defineProps<{
  placeholder: string
  sendLabel: string
  loading?: boolean
  disabled?: boolean
  disabledHint?: string
}>(), {
  loading: false,
  disabled: false,
  disabledHint: '',
})

const emit = defineEmits<{
  send: []
  cancel: []
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <!-- 兼容旧引用：输入区统一由已有 ChatMessageForm 完成。 -->
  <ChatMessageForm
    v-model="model"
    :placeholder="placeholder"
    :send-label="sendLabel"
    :loading="loading"
    :disabled="disabled"
    :disabled-hint="disabledHint"
    @send="emit('send')"
    @cancel="emit('cancel')"
  />
</template>
