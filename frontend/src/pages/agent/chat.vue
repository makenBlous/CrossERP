<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'
import { createAgentAdapter } from '@/agent/index'
import type { AgentCard, AgentPart } from '@/agent/adapter'
import { fetchChat } from '@/api/agent'
import { recordAgentQuestion, recordSuggestionStep } from '@/api/agent-module'
import { submitAgentSuggestion } from '@/api/workflows'
import { useSessionStore } from '@/stores/session'
import type { ChatMessage, ChatThread } from '@/types/domain'
import ChatLog from '@/views/apps/chat/ChatLog.vue'
import ChatMessageForm from '@/views/apps/chat/ChatMessageForm.vue'
import { can } from '@/utils/permission'

definePage({ meta: { layoutWrapperClasses: 'layout-content-height-fixed' } })

interface Bubble extends ChatMessage { card?: AgentCard; submitted?: boolean }

const { t, locale } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { isLeftSidebarOpen } = useResponsiveLeftSidebar()
const threads = ref<ChatThread[]>([])
const bubbles = ref<Bubble[]>([])
const draft = ref('')
const query = ref('')
const activeId = ref('th-1')
const sending = ref(false)
const latestRunId = ref<string | null>(null)
const adapter = createAgentAdapter()
const canSuggest = computed(() => can(session.role, 'suggest'))
const activeThread = computed(() => threads.value.find(item => item.id === activeId.value))
const visibleThreads = computed(() => threads.value.filter(item => item.title.toLowerCase().includes(query.value.trim().toLowerCase())))

// 改编自 Vuexy apps/chat.vue 的 scrollToBottomInChatLog：新消息和建议卡出现后滚到底部。
const chatLogPS = ref()

function scrollToBottomInChatLog() {
  const scrollEl = chatLogPS.value?.$el || chatLogPS.value
  if (scrollEl)
    scrollEl.scrollTop = scrollEl.scrollHeight
}

watch(() => [bubbles.value.length, bubbles.value[bubbles.value.length - 1]?.text, sending.value], () => nextTick(scrollToBottomInChatLog))

onMounted(async () => {
  const payload = await fetchChat()

  threads.value = payload.threads
  bubbles.value = payload.messages.map(message => ({ ...message }))
})

function pushPart(part: AgentPart) {
  const last = bubbles.value[bubbles.value.length - 1]
  if (part.kind === 'text' && last?.role === 'assistant' && !last.card) {
    last.text += part.text ?? ''

    return
  }
  bubbles.value.push({ id: `local-${bubbles.value.length + 1}`, role: 'assistant', text: part.text ?? '', card: part.card })
}

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value)
    return
  draft.value = ''
  sending.value = true
  bubbles.value.push({ id: `local-${bubbles.value.length + 1}`, role: 'user', text })
  try {
    const run = await recordAgentQuestion(text)

    latestRunId.value = run.id
    await adapter.sendMessage({ pageName: t('agentModule.chat.title'), route: '/agent/chat', selectedId: null, locale: String(locale.value).startsWith('en') ? 'en' : 'zh-CN' }, text, pushPart)
  }
  catch (error) {
    bubbles.value.push({ id: `error-${bubbles.value.length + 1}`, role: 'assistant', text: error instanceof Error ? error.message : t('foundation.errorTitle') })
  }
  finally {
    sending.value = false
  }
}

async function submitSuggestion(message: Bubble) {
  if (!message.card?.draft || !canSuggest.value)
    return
  const approval = await submitAgentSuggestion(message.card.draft)

  message.submitted = true
  if (latestRunId.value)
    await recordSuggestionStep(latestRunId.value, approval.id)
}
</script>

<template>
  <VLayout
    class="chat-app-layout"
    style="z-index: 0;"
  >
    <VNavigationDrawer
      v-model="isLeftSidebarOpen"
      absolute
      touchless
      location="start"
      width="370"
      class="chat-list-sidebar"
      :temporary="$vuetify.display.smAndDown"
      :permanent="$vuetify.display.mdAndUp"
    >
      <div class="chat-list-header d-flex align-center">
        <AppTextField
          v-model="query"
          :placeholder="t('chat.threads')"
          density="compact"
        />
      </div>
      <VDivider />
      <PerfectScrollbar
        tag="ul"
        class="chat-contacts-list px-3 py-2"
        :options="{ wheelPropagation: false }"
      >
        <li
          v-for="thread in visibleThreads"
          :key="thread.id"
          class="chat-contact cursor-pointer d-flex align-center"
          :class="{ 'chat-contact-active': thread.id === activeId }"
          @click="activeId = thread.id; isLeftSidebarOpen = false"
        >
          <VAvatar
            size="40"
            color="primary"
            variant="tonal"
          >
            <span>{{ thread.title.slice(0, 1) }}</span>
          </VAvatar>
          <div class="flex-grow-1 ms-4 overflow-hidden">
            <p class="text-base text-high-emphasis mb-0">
              {{ thread.title }}
            </p><p class="mb-0 text-truncate text-body-2">
              {{ thread.updatedAt }}
            </p>
          </div>
        </li>
      </PerfectScrollbar>
    </VNavigationDrawer>
    <VMain class="chat-content-container">
      <div class="d-flex flex-column h-100">
        <div class="active-chat-header d-flex align-center text-medium-emphasis bg-surface">
          <IconBtn
            class="d-md-none me-3"
            @click="isLeftSidebarOpen = true"
          >
            <VIcon icon="tabler-menu-2" />
          </IconBtn>
          <VAvatar
            size="40"
            color="primary"
            variant="tonal"
          >
            <VIcon icon="tabler-message-chatbot" />
          </VAvatar>
          <div class="flex-grow-1 ms-4 overflow-hidden">
            <div class="text-h6 mb-0 font-weight-regular">
              {{ activeThread?.title || t('chat.title') }}
            </div><p class="text-truncate mb-0 text-body-2">
              {{ t('agentModule.chat.subtitle') }}
            </p>
          </div>
        </div>
        <VDivider />
        <VAlert
          type="warning"
          variant="tonal"
          class="ma-4 mb-0"
        >
          {{ t('common.aiNoLedger') }}
        </VAlert>
        <PerfectScrollbar
          ref="chatLogPS"
          :options="{ wheelPropagation: false }"
          class="flex-grow-1"
        >
          <ChatLog
            :messages="bubbles"
            :contact-name="t('chat.title')"
            :self-name="session.displayName"
          >
            <template #after="{ message }">
              <VCard
                v-if="message.card"
                variant="tonal"
                :color="message.card.kind === 'suggestion' ? 'warning' : 'info'"
                class="mt-2"
              >
                <VCardItem>
                  <VCardTitle class="text-body-1">
                    {{ message.card.title }}
                  </VCardTitle>
                </VCardItem>
                <VCardText>
                  <div
                    v-for="line in message.card.lines"
                    :key="line.label"
                    class="d-flex justify-space-between gap-4 text-body-2"
                  >
                    <span>{{ line.label }}</span><strong>{{ line.value }}</strong>
                  </div>
                  <VBtn
                    v-if="message.card.draft"
                    class="mt-3"
                    size="small"
                    :disabled="message.submitted || !canSuggest"
                    @click="submitSuggestion(message)"
                  >
                    {{ message.submitted ? t('assistant.submitted') : t('assistant.submit') }}
                  </VBtn>
                </VCardText>
              </VCard>
            </template>
          </ChatLog>
          <div
            v-if="sending"
            class="text-caption text-medium-emphasis px-6 pb-4"
          >
            {{ t('assistant.thinking') }}
          </div>
        </PerfectScrollbar>
        <VDivider /><ChatMessageForm
          v-model="draft"
          :placeholder="t('agentModule.chat.placeholder')"
          :send-label="t('chat.send')"
          :loading="sending"
          @send="send"
        />
      </div>
    </VMain>
  </VLayout>
</template>

<style lang="scss">
@use "@styles/variables/vuetify";
@use "@core/scss/base/mixins";
.chat-app-layout { border-radius: vuetify.$card-border-radius; @include mixins.elevation(vuetify.$card-elevation); .chat-list-header, .active-chat-header { min-block-size: 76px; padding-inline: 1.5rem; } }
.chat-contact { border-radius: .375rem; padding-block: .75rem; padding-inline: .75rem; &.chat-contact-active { background: rgba(var(--v-theme-primary), .12); } }
</style>
