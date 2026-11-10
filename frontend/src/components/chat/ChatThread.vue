<script setup lang="ts">
import ChatComposer from './ChatComposer.vue'
import ChatMessage from './ChatMessage.vue'
import ChatStatusLine from './ChatStatusLine.vue'
import type { ChatDisplayMessage, ChatState } from './types'

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
}>(), {
  loading: false,
  state: 'idle',
  statusText: '',
  aiEnabled: true,
  disabledReason: '',
})

const emit = defineEmits<{
  send: []
  retry: []
  cancel: []
}>()

const draft = defineModel<string>({ required: true })
const log = ref<HTMLElement | null>(null)

async function scrollToLatest() {
  await nextTick()
  if (log.value)
    log.value.scrollTop = log.value.scrollHeight
}

watch(() => props.messages.map(message => `${message.id}:${message.text}`).join('|'), scrollToLatest)
watch(() => props.loading, scrollToLatest)
onMounted(scrollToLatest)
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
        <VIcon
          icon="tabler-message-chatbot"
          size="30"
        />
        <span>从一个问题开始，助手只读取已存储的数据。</span>
      </div>
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
        :assistant-name="assistantName"
        :self-name="selfName"
      >
        <template #default>
          <slot
            name="message-after"
            :message="message"
          />
        </template>
      </ChatMessage>
      <ChatStatusLine
        :state="state"
        :text="statusText"
        @retry="emit('retry')"
        @cancel="emit('cancel')"
      />
    </div>
    <ChatComposer
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
  padding: 1.25rem clamp(.85rem, 3vw, 2rem) .4rem;
  scroll-behavior: smooth;
}

.chat-thread__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: .65rem;
  min-block-size: 8rem;
  color: rgba(var(--v-theme-on-surface), .55);
  text-align: center;
}
</style>
