<script setup lang="ts">
import type { ChatState } from './types'

defineProps<{
  state: ChatState
  text?: string
}>()

const emit = defineEmits<{
  retry: []
  cancel: []
}>()
</script>

<template>
  <div
    v-if="state !== 'idle'"
    class="chat-status-line"
    :class="`chat-status-line--${state}`"
    role="status"
  >
    <VProgressCircular
      v-if="state === 'loading'"
      indeterminate
      size="18"
      width="2"
      color="primary"
    />
    <VIcon
      v-else
      :icon="state === 'error' ? 'tabler-alert-circle' : 'tabler-circle-check'"
      size="18"
    />
    <span class="flex-grow-1">{{ text }}</span>
    <VBtn
      v-if="state === 'loading'"
      variant="text"
      size="small"
      @click="emit('cancel')"
    >
      取消
    </VBtn>
    <VBtn
      v-if="state === 'error'"
      variant="text"
      size="small"
      @click="emit('retry')"
    >
      重试
    </VBtn>
  </div>
</template>

<style scoped>
.chat-status-line {
  display: flex;
  align-items: center;
  gap: .6rem;
  margin-inline: .25rem;
  border-radius: .75rem;
  padding: .55rem .75rem;
  color: rgba(var(--v-theme-on-surface), .65);
  font-size: .8rem;
}

.chat-status-line--error {
  background: rgba(var(--v-theme-error), .08);
  color: rgb(var(--v-theme-error));
}

.chat-status-line--cancelled {
  background: rgba(var(--v-theme-on-surface), .04);
}
</style>
