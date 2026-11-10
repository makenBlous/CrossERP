<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'
import { createAgentAdapter } from '@/agent/index'
import type { AgentCard, AgentPart } from '@/agent/adapter'
import { fetchChat } from '@/api/agent'
import { recordAgentQuestion, recordSuggestionStep } from '@/api/agent-module'
import { submitAgentSuggestion } from '@/api/workflows'
import ChatThread from '@/components/chat/ChatThread.vue'
import type { ChatState } from '@/components/chat/types'
import { useChatHistory } from '@/components/chat/useChatHistory'
import { useChatInflight } from '@/components/chat/useChatInflight'
import { useAiModeStore } from '@/stores/ai-mode'
import { useSessionStore } from '@/stores/session'
import type { ChatMessage, ChatThread as ChatThreadModel } from '@/types/domain'
import { can } from '@/utils/permission'

definePage({ meta: { layoutWrapperClasses: 'layout-content-height-fixed' } })

interface Bubble extends ChatMessage {
  card?: AgentCard
  submitted?: boolean
  local?: boolean
}

const { t, locale } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const aiMode = useAiModeStore()
const { isLeftSidebarOpen } = useResponsiveLeftSidebar()
const threads = ref<ChatThreadModel[]>([])
const bubbles = ref<Bubble[]>([])
const draft = ref('')
const query = ref('')
const activeId = ref('th-1')
const sending = ref(false)
const state = ref<ChatState>('idle')
const statusText = ref('')
const lastPrompt = ref('')
const latestRunId = ref<string | null>(null)
const adapter = createAgentAdapter()

const inflight = useChatInflight({
  userId: () => session.userId,
  isLoggedIn: () => session.isLoggedIn,
  role: () => session.role,
  sending,
  state,
  statusText,
})

const history = useChatHistory<Bubble>('agent-center', computed(() => session.userId), computed(() => session.isLoggedIn))
const hydratedUserId = ref<string | null>(null)
const hydrating = ref(false)
const canSuggest = computed(() => can(session.role, 'suggest'))
const activeThread = computed(() => threads.value.find(item => item.id === activeId.value))
const visibleThreads = computed(() => threads.value.filter(item => item.title.toLowerCase().includes(query.value.trim().toLowerCase())))

watch(bubbles, value => {
  if (!hydrating.value && inflight.canPersist(hydratedUserId.value))
    history.save(value)
}, { deep: true })

async function loadChat() {
  const userId = session.isLoggedIn ? session.userId : null

  hydrating.value = true
  bubbles.value = []

  if (!userId) {
    threads.value = []
    hydratedUserId.value = null
    hydrating.value = false

    return
  }

  const payload = await fetchChat()

  if (!session.isLoggedIn || session.userId !== userId)
    return

  threads.value = payload.threads
  bubbles.value = history.load(payload.messages.map(message => ({ ...message, local: false })))
  hydratedUserId.value = userId
  hydrating.value = false
}

onMounted(loadChat)
inflight.watchIdentity(loadChat)

function pushPart(part: AgentPart) {
  const last = bubbles.value[bubbles.value.length - 1]

  if (part.kind === 'text' && last?.local && last.role === 'assistant' && !last.card) {
    last.text += part.text ?? ''

    return
  }

  bubbles.value.push({ id: `local-${bubbles.value.length + 1}`, role: 'assistant', text: part.text ?? '', card: part.card, local: true })
}

async function sendMessage(text: string) {
  if (!aiMode.isEnabled || !text || sending.value)
    return

  const ticket = inflight.begin()

  draft.value = ''
  sending.value = true
  state.value = 'loading'
  statusText.value = '正在读取只读数据…'
  lastPrompt.value = text
  bubbles.value.push({ id: `local-${bubbles.value.length + 1}`, role: 'user', text, local: true })

  try {
    const run = await recordAgentQuestion(text)

    if (!inflight.isCurrent(ticket))
      return

    latestRunId.value = run.id
    await adapter.sendMessage({ pageName: t('agentModule.chat.title'), route: '/agent/chat', selectedId: null, locale: String(locale.value).startsWith('en') ? 'en' : 'zh-CN' }, text, part => {
      inflight.writeIfCurrent(ticket, () => pushPart(part))
    })
    if (inflight.isLatest(ticket)) {
      state.value = 'idle'
      statusText.value = ''
    }
  }
  catch (error) {
    if (inflight.isLatest(ticket)) {
      state.value = 'error'
      statusText.value = error instanceof Error ? error.message : t('foundation.errorTitle')
    }
  }
  finally {
    if (inflight.isLatest(ticket))
      sending.value = false
  }
}

function send() {
  sendMessage(draft.value.trim())
}

function retry() {
  sendMessage(lastPrompt.value)
}

function cancel() {
  if (!sending.value) {
    isLeftSidebarOpen.value = false

    return
  }

  inflight.invalidate()
  sending.value = false
  state.value = 'cancelled'
  statusText.value = '已取消本次请求。'
}

async function submitSuggestion(message: { id: string }) {
  const bubble = bubbles.value.find(item => item.id === message.id)

  if (!bubble?.card?.draft || !canSuggest.value)
    return
  const approval = await submitAgentSuggestion(bubble.card.draft)

  bubble.submitted = true
  if (latestRunId.value)
    await recordSuggestionStep(latestRunId.value, approval.id)
}
</script>

<template>
  <VLayout
    class="chat-app-layout"
    style="z-index: 0;"
    @keydown.esc="isLeftSidebarOpen = false"
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
      <div class="chat-list-caption px-5 py-3 text-caption text-medium-emphasis">
        我的会话
      </div>
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
            </p>
            <p class="mb-0 text-truncate text-body-2 text-medium-emphasis">
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
            </div>
            <p class="text-truncate mb-0 text-body-2">
              {{ t('agentModule.chat.subtitle') }}
            </p>
          </div>
          <VChip
            size="small"
            color="primary"
            variant="tonal"
          >
            只读助手
          </VChip>
        </div>
        <VDivider />
        <VAlert
          v-if="!aiMode.isEnabled"
          type="info"
          variant="tonal"
          class="ma-4 mb-0"
        >
          {{ t('assistant.aiClosed') }}
        </VAlert>
        <ChatThread
          v-model="draft"
          :messages="bubbles"
          :assistant-name="t('chat.title')"
          :self-name="session.displayName"
          :placeholder="t('agentModule.chat.placeholder')"
          :send-label="t('chat.send')"
          :loading="sending"
          :state="state"
          :status-text="statusText"
          :ai-enabled="aiMode.isEnabled"
          :disabled-reason="t('assistant.aiClosed')"
          @send="send"
          @retry="retry"
          @cancel="cancel"
        >
          <template #message-after="{ message }">
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
        </ChatThread>
      </div>
    </VMain>
  </VLayout>
</template>

<style lang="scss">
@use "@styles/variables/vuetify";
@use "@core/scss/base/mixins";

.chat-app-layout {
  border-radius: vuetify.$card-border-radius;
  @include mixins.elevation(vuetify.$card-elevation);

  .chat-list-header,
  .active-chat-header {
    min-block-size: 76px;
    padding-inline: 1.5rem;
  }
}

.chat-contact {
  border-radius: .375rem;
  padding-block: .75rem;
  padding-inline: .75rem;

  &.chat-contact-active {
    background: rgba(var(--v-theme-primary), .12);
  }
}

.chat-thread {
  min-block-size: 0;
  flex: 1 1 auto;
}
</style>
