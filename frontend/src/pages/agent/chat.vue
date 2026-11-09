<script setup lang="ts">
import { fetchChat } from '@/api/agent'
import { useSessionStore } from '@/stores/session'
import type { ChatMessage, ChatThread } from '@/types/domain'

definePage({
  meta: {
    layoutWrapperClasses: 'layout-content-height-fixed',
  },
})

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const threads = ref<ChatThread[]>([])
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const activeId = ref('th-1')

const canSubmit = computed(() => session.role === 'admin' || session.role === 'operator' || session.role === 'finance')

onMounted(async () => {
  const payload = await fetchChat()

  threads.value = payload.threads
  messages.value = payload.messages
})

function send() {
  const text = draft.value.trim()

  if (!text)
    return

  messages.value.push({
    id: `local-${messages.value.length + 1}`,
    role: 'user',
    text,
  })
  messages.value.push({
    id: `local-a-${messages.value.length + 1}`,
    role: 'assistant',
    text: t('chat.echo'),
  })
  draft.value = ''
}

function submitSuggestion(message: ChatMessage) {
  if (!message.suggestion || !canSubmit.value)
    return

  message.suggestion.status = 'submitted'
}
</script>

<template>
  <VCard class="chat-shell d-flex">
    <div class="chat-side pa-4">
      <div class="text-h6 mb-4">
        {{ t('chat.threads') }}
      </div>
      <VList
        nav
        :selected="[activeId]"
      >
        <VListItem
          v-for="thread in threads"
          :key="thread.id"
          :value="thread.id"
          @click="activeId = thread.id"
        >
          <VListItemTitle>{{ thread.title }}</VListItemTitle>
          <VListItemSubtitle>{{ thread.updatedAt }}</VListItemSubtitle>
        </VListItem>
      </VList>
    </div>
    <div class="chat-main d-flex flex-column flex-grow-1">
      <div class="pa-4 border-b">
        <div class="text-h5">
          {{ t('chat.title') }}
        </div>
        <div class="text-body-2 text-medium-emphasis">
          {{ t('chat.subtitle') }}
        </div>
      </div>
      <div class="flex-grow-1 pa-4 chat-log">
        <VAlert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          {{ t('common.aiNoLedger') }}
        </VAlert>
        <div
          v-for="message in messages"
          :key="message.id"
          class="mb-4"
          :class="message.role === 'user' ? 'd-flex justify-end' : ''"
        >
          <VCard
            :color="message.role === 'user' ? 'primary' : undefined"
            :variant="message.role === 'user' ? 'flat' : 'outlined'"
            max-width="640"
          >
            <VCardText>
              <div :class="message.role === 'user' ? 'text-white' : ''">
                {{ message.text }}
              </div>
              <VCard
                v-if="message.toolCall"
                variant="tonal"
                color="info"
                class="mt-3"
              >
                <VCardItem>
                  <VCardTitle class="text-body-1">
                    {{ t('chat.toolCall') }} · {{ message.toolCall.name }}
                  </VCardTitle>
                </VCardItem>
                <VCardText>
                  <div class="text-caption text-medium-emphasis mb-1">
                    {{ t('chat.args') }}
                  </div>
                  <div
                    v-for="(value, key) in message.toolCall.args"
                    :key="key"
                    class="text-body-2"
                  >
                    {{ key }}: {{ value }}
                  </div>
                  <div class="text-caption text-medium-emphasis mt-3 mb-1">
                    {{ t('chat.result') }}
                  </div>
                  <div>{{ message.toolCall.summary }}</div>
                </VCardText>
              </VCard>
              <VCard
                v-if="message.suggestion"
                variant="tonal"
                color="warning"
                class="mt-3"
              >
                <VCardItem>
                  <VCardTitle class="text-body-1">
                    {{ t('chat.suggestion') }}
                  </VCardTitle>
                  <VCardSubtitle>{{ message.suggestion.title }}</VCardSubtitle>
                </VCardItem>
                <VCardText>
                  <p>{{ message.suggestion.detail }}</p>
                  <div class="font-weight-medium mb-3">
                    {{ message.suggestion.amountLabel }}
                  </div>
                  <VBtn
                    v-if="message.suggestion.status === 'draft'"
                    size="small"
                    :disabled="!canSubmit"
                    @click="submitSuggestion(message)"
                  >
                    {{ t('chat.submit') }}
                  </VBtn>
                  <VChip
                    v-else
                    color="success"
                    size="small"
                  >
                    {{ t('chat.submitted') }}
                  </VChip>
                </VCardText>
              </VCard>
            </VCardText>
          </VCard>
        </div>
      </div>
      <div class="pa-4 d-flex gap-3">
        <AppTextField
          v-model="draft"
          :placeholder="t('chat.placeholder')"
          @keyup.enter="send"
        />
        <VBtn @click="send">
          {{ t('chat.send') }}
        </VBtn>
      </div>
    </div>
  </VCard>
</template>

<style scoped>
.chat-shell {
  min-height: 640px;
}

.chat-side {
  width: 280px;
  border-inline-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.chat-log {
  overflow: auto;
  max-height: 560px;
}

@media (max-width: 800px) {
  .chat-side {
    display: none;
  }
}
</style>
