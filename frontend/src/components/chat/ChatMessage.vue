<script setup lang="ts">
import type { ChatDisplayMessage } from './types'

const props = defineProps<{
  message: ChatDisplayMessage
  assistantName: string
  selfName: string
}>()

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll('\'', '&#039;')
}

function renderMarkdown(source: string) {
  const blocks: string[] = []
  let html = escapeHtml(source).replace(/```(\w*)\n([\s\S]*?)```/g, (_match, language: string, code: string) => {
    const index = blocks.push(`<pre class="chat-code"><code data-language="${language}">${code.trimEnd()}</code></pre>`) - 1

    return `__CHAT_CODE_${index}__`
  })

  html = html.replace(/^[-*] ([^\n]*)$/gm, '<li>$1</li>')
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
  html = html.replace(/\n/g, '<br>')
  html = html.replace(/__CHAT_CODE_(\d+)__/g, (_match, index: string) => blocks[Number(index)] ?? '')

  return html
}

const renderedText = computed(() => renderMarkdown(props.message.text))
const displayName = computed(() => props.message.role === 'user' ? props.selfName : props.assistantName)
</script>

<template>
  <article
    class="chat-message"
    :class="`chat-message--${message.role}`"
    :data-message-id="message.id"
  >
    <VAvatar
      size="34"
      :color="message.role === 'user' ? 'primary' : 'secondary'"
      variant="tonal"
      class="chat-message__avatar"
    >
      <span>{{ displayName.slice(0, 1) }}</span>
    </VAvatar>
    <div class="chat-message__body">
      <div class="chat-message__meta">
        <span>{{ displayName }}</span>
        <span v-if="message.time">{{ message.time }}</span>
      </div>
      <div
        class="chat-message__bubble"
        :class="message.role === 'user' ? 'chat-message__bubble--user' : 'chat-message__bubble--assistant'"
      >
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          class="chat-markdown"
          v-html="renderedText"
        />
        <div
          v-if="message.toolCall"
          class="chat-tool-call"
        >
          <div class="d-flex align-center gap-2 text-caption font-weight-medium">
            <VIcon
              icon="tabler-tool"
              size="16"
            />
            {{ message.toolCall.name }}
          </div>
          <div class="text-caption text-medium-emphasis mt-1">
            {{ message.toolCall.summary }}
          </div>
        </div>
      </div>
      <slot :message="message" />
    </div>
  </article>
</template>

<style scoped lang="scss">
.chat-message {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  max-inline-size: min(100%, 860px);
  margin-block-end: 1.25rem;

  &--user {
    flex-direction: row-reverse;
    margin-inline-start: auto;
  }
}

.chat-message__body {
  min-inline-size: 0;
  max-inline-size: min(100%, 720px);
}

.chat-message__meta {
  display: flex;
  gap: .5rem;
  align-items: center;
  margin-block-end: .3rem;
  color: rgba(var(--v-theme-on-surface), .6);
  font-size: .75rem;
}

.chat-message--user .chat-message__meta {
  justify-content: flex-end;
}

.chat-message__bubble {
  border: 1px solid rgba(var(--v-theme-on-surface), .08);
  border-radius: 1rem;
  padding: .8rem 1rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.chat-message__bubble--assistant {
  border-start-start-radius: .35rem;
  background: rgba(var(--v-theme-on-surface), .045);
}

.chat-message__bubble--user {
  border-start-end-radius: .35rem;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.chat-markdown :deep(p) {
  margin-block: 0;
}

.chat-markdown :deep(ul) {
  margin-block: .45rem 0;
  padding-inline-start: 1.2rem;
}

.chat-markdown :deep(.chat-code) {
  max-inline-size: 100%;
  margin-block: .75rem 0;
  border-radius: .65rem;
  background: rgba(0, 0, 0, .28);
  color: #f4f6ff;
  overflow: auto;
  padding: .75rem;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: .78rem;
  line-height: 1.5;
  white-space: pre;
}

.chat-tool-call {
  margin-block-start: .75rem;
  border-block-start: 1px solid rgba(var(--v-theme-on-surface), .12);
  padding-block-start: .6rem;
}
</style>
