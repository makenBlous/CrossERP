<script setup lang="ts">
import ChatStatusLine from './ChatStatusLine.vue'
import type { ChatDisplayMessage, ChatState, ChatSuggestion } from './types'
import ChatLog from '@/views/apps/chat/ChatLog.vue'
import ChatMessageForm from '@/views/apps/chat/ChatMessageForm.vue'

const props = withDefaults(defineProps<{
  messages: ChatDisplayMessage[]
  assistantName: string
  selfName: string
  placeholder: string
  sendLabel: string
  loading?: boolean
  state?: ChatState
  statusText?: string
  aiEnabled?: boolean
  disabledReason?: string
  emptyTitle?: string
  emptyText?: string
  suggestions?: ChatSuggestion[]
  sourceLabel?: string
}>(), {
  loading: false,
  state: 'idle',
  statusText: '',
  aiEnabled: true,
  disabledReason: '',
  emptyTitle: '从一个问题开始',
  emptyText: '助手只读取已存储的数据，并把写操作整理成待审批建议。',
  suggestions: () => [],
  sourceLabel: '只读数据 · CrossERP 已存储记录',
})

const emit = defineEmits<{
  send: []
  retry: []
  cancel: []
  suggestion: [prompt: string]
}>()

const draft = defineModel<string>({ required: true })
const log = ref<HTMLElement | null>(null)
const copiedMessageId = ref<string | null>(null)

async function scrollToLatest() {
  await nextTick()
  if (!log.value)
    return

  log.value.scrollTop = props.messages.length ? log.value.scrollHeight : 0
}

watch(() => props.messages.map(message => `${message.id}:${message.text}`).join('|'), scrollToLatest)
watch(() => props.loading, scrollToLatest)
onMounted(scrollToLatest)

async function copyMessage(message: ChatDisplayMessage) {
  if (!navigator.clipboard)
    return

  await navigator.clipboard.writeText(message.text)
  copiedMessageId.value = message.id
  window.setTimeout(() => {
    if (copiedMessageId.value === message.id)
      copiedMessageId.value = null
  }, 1600)
}
</script>

<template>
  <section class="chat-thread">
    <div
      ref="log"
      class="chat-thread__log"
      aria-live="polite"
    >
      <div
        v-if="!messages.length"
        class="chat-thread__empty"
      >
        <div class="chat-thread__empty-icon">
          <VIcon
            icon="tabler-message-chatbot"
            size="28"
          />
        </div>
        <div>
          <p class="chat-thread__empty-title">{{ emptyTitle }}</p>
          <p class="chat-thread__empty-text">{{ emptyText }}</p>
        </div>
      </div>
      <div
        v-if="!messages.length && suggestions.length"
        class="chat-thread__suggestions"
      >
        <VBtn
          v-for="suggestion in suggestions"
          :key="suggestion.id"
          variant="tonal"
          color="primary"
          size="small"
          rounded="pill"
          :disabled="!aiEnabled"
          @click="emit('suggestion', suggestion.prompt)"
        >
          <VIcon
            v-if="suggestion.icon"
            :icon="suggestion.icon"
            size="16"
            class="me-1"
          />
          {{ suggestion.label }}
        </VBtn>
      </div>
      <ChatLog
        :messages="messages"
        :contact-name="assistantName"
        :self-name="selfName"
        :source-label="sourceLabel"
        :padded="false"
      >
        <template #after="{ message }">
          <slot
            name="message-after"
            :message="message"
          />
          <div
            v-if="message.role === 'assistant'"
            class="chat-thread__message-actions"
          >
            <VBtn
              variant="text"
              size="x-small"
              :aria-label="copiedMessageId === message.id ? '已复制' : '复制回复'"
              @click="copyMessage(message)"
            >
              <VIcon
                :icon="copiedMessageId === message.id ? 'tabler-check' : 'tabler-copy'"
                size="15"
              />
              <span>{{ copiedMessageId === message.id ? '已复制' : '复制' }}</span>
            </VBtn>
            <VBtn
              variant="text"
              size="x-small"
              aria-label="重新生成"
              @click="emit('retry')"
            >
              <VIcon
                icon="tabler-refresh"
                size="15"
              />
              <span>重新生成</span>
            </VBtn>
          </div>
        </template>
      </ChatLog>
      <ChatStatusLine
        :state="state"
        :text="statusText"
        @retry="emit('retry')"
        @cancel="emit('cancel')"
      />
    </div>
    <ChatMessageForm
      v-model="draft"
      :placeholder="placeholder"
      :send-label="sendLabel"
      :loading="loading"
      :disabled="!aiEnabled"
      :disabled-hint="disabledReason"
      @send="emit('send')"
      @cancel="emit('cancel')"
    />
  </section>
</template>

<style scoped>
.chat-thread {
  display: flex;
  min-block-size: 0;
  block-size: 100%;
  flex-direction: column;
  background: rgb(var(--v-theme-surface));
}

.chat-thread__log {
  flex: 1 1 auto;
  min-block-size: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 1.4rem clamp(.9rem, 3vw, 2.4rem) .4rem;
  scroll-behavior: smooth;
}

.chat-thread__empty {
  display: grid;
  align-content: center;
  justify-content: center;
  gap: 1rem;
  min-block-size: 12rem;
  margin-block-start: 2rem;
  color: rgba(var(--v-theme-on-surface), .72);
  text-align: start;
}

.chat-thread__empty-icon {
  display: grid;
  place-items: center;
  inline-size: 3.25rem;
  block-size: 3.25rem;
  border-radius: 1.1rem;
  background: rgba(var(--v-theme-primary), .12);
  color: rgb(var(--v-theme-primary));
}

.chat-thread__empty-title {
  margin: 0;
  color: rgb(var(--v-theme-on-surface));
  font-size: 1rem;
  font-weight: 600;
}

.chat-thread__empty-text {
  max-inline-size: 38rem;
  margin: .35rem 0 0;
  color: rgba(var(--v-theme-on-surface), .58);
  font-size: .875rem;
  line-height: 1.6;
}

.chat-thread__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  margin-block: 0 1.5rem;
}

.chat-thread__message-actions {
  display: flex;
  gap: .15rem;
  margin-block: .15rem .45rem;
  color: rgba(var(--v-theme-on-surface), .52);
}

@media (max-width: 600px) {
  .chat-thread__log { padding-inline: .75rem; }
  .chat-thread__empty { min-block-size: 10rem; }
  .chat-thread__message-actions span { display: none; }
}
</style>
