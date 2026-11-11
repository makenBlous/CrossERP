<script setup lang="ts">
import type { AgentCard, AgentPart } from '@/agent/adapter'
import { createAgentAdapter } from '@/agent/index'
import { submitAgentSuggestion } from '@/api/agent-module'
import ChatThread from '@/components/chat/ChatThread.vue'
import type { ChatState, ChatSuggestion } from '@/components/chat/types'
import { useChatHistory } from '@/components/chat/useChatHistory'
import { useChatInflight } from '@/components/chat/useChatInflight'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { usePageContext } from '@/composables/usePageContext'
import { pageCatalog } from '@/config/pages'
import { useSessionStore } from '@/stores/session'
import { useAiModeStore } from '@/stores/ai-mode'
import { can } from '@/utils/permission'

interface Bubble {
  id: string
  role: 'user' | 'assistant'
  text: string
  card?: AgentCard
  submitted?: boolean
  local?: boolean
}

const { t, locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const session = useSessionStore()
const aiMode = useAiModeStore()
const pageContext = usePageContext()
const open = ref(false)
const draft = ref('')
const sending = ref(false)
const bubbles = ref<Bubble[]>([])
const state = ref<ChatState>('idle')
const statusText = ref('')
const lastPrompt = ref('')
const adapter = createAgentAdapter()

const inflight = useChatInflight({
  userId: () => session.userId,
  isLoggedIn: () => session.isLoggedIn,
  role: () => session.role,
  sending,
  state,
  statusText,
})

const history = useChatHistory<Bubble>('assistant', computed(() => session.userId), computed(() => session.isLoggedIn))
const hydratedUserId = ref<string | null>(null)
const hydrating = ref(false)

const canSuggest = computed(() => can(session.role, 'suggest'))
const showFloatingEntry = computed(() => route.path !== '/agent/chat')

watch(bubbles, value => {
  if (!hydrating.value && inflight.canPersist(hydratedUserId.value))
    history.save(value)
}, { deep: true })

function loadHistory() {
  const userId = session.isLoggedIn ? session.userId : null

  hydrating.value = true
  bubbles.value = userId ? history.load([]) : []
  hydratedUserId.value = userId
  nextTick(() => {
    hydrating.value = false
  })
}

onMounted(() => {
  loadHistory()
  window.addEventListener('keydown', onWindowKeydown)
})

inflight.watchIdentity(loadHistory)

onBeforeUnmount(() => window.removeEventListener('keydown', onWindowKeydown))

function onWindowKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && open.value && !sending.value)
    open.value = false
}

function matchPage(path: string) {
  const ranked = [...pageCatalog].filter(item => item.path !== '/*').sort((a, b) => b.path.length - a.path.length)

  return ranked.find(item => {
    const pattern = `^${item.path.replace(/:[^/]+/g, '[^/]+')}$`

    return new RegExp(pattern).test(path)
  })
}

const page = computed(() => matchPage(route.path))
const pageName = computed(() => page.value?.name[String(locale.value).startsWith('en') ? 'en' : 'zh-CN'] ?? route.path)

const suggestions = computed<ChatSuggestion[]>(() => {
  if (!can(session.role, 'view'))
    return []

  const pageLabel = pageName.value || '当前页面'

  const items: ChatSuggestion[] = [
    {
      id: 'page-summary',
      label: `概览${pageLabel}`,
      prompt: `请概览${pageLabel}当前已存储的数据，并标出需要人工关注的地方。`,
      icon: 'tabler-sparkles',
    },
    {
      id: 'page-exceptions',
      label: '找出异常与原因',
      prompt: `请从${pageLabel}相关的已存储记录中找出异常，并说明原因码或来源。`,
      icon: 'tabler-alert-circle',
    },
  ]

  if (canSuggest.value) {
    items.push({
      id: 'draft-suggestion',
      label: '起草待审批建议',
      prompt: `请基于${pageLabel}的已存储数据起草一条待审批建议，不要直接修改业务数据。`,
      icon: 'tabler-bulb',
    })
  }

  return items
})

const selectedId = computed(() => {
  if (pageContext.selectedRecordId.value)
    return pageContext.selectedRecordId.value

  const params = route.params as Record<string, string | string[] | undefined>
  const value = params.id

  return Array.isArray(value) ? value[0] ?? null : value ?? null
})

function pushPart(part: AgentPart) {
  const last = bubbles.value[bubbles.value.length - 1]

  if (part.kind === 'text' && last?.local && last.role === 'assistant' && !last.card) {
    last.text += part.text ?? ''

    return
  }

  bubbles.value.push({
    id: `a-${bubbles.value.length + 1}`,
    role: 'assistant',
    text: part.text ?? '',
    card: part.card,
    local: true,
  })
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
  bubbles.value.push({ id: `u-${bubbles.value.length + 1}`, role: 'user', text, local: true })

  try {
    await adapter.sendMessage({
      pageName: pageName.value,
      route: route.path,
      selectedId: selectedId.value,
      locale: String(locale.value).startsWith('en') ? 'en' : 'zh-CN',
    }, text, part => {
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
    open.value = false

    return
  }

  inflight.invalidate()
  sending.value = false
  state.value = 'cancelled'
  statusText.value = '已取消本次请求。'
}

async function submit(message: { id: string }) {
  const bubble = bubbles.value.find(item => item.id === message.id)

  if (!bubble?.card?.draft || !canSuggest.value)
    return

  await submitAgentSuggestion(bubble.card.draft)
  bubble.submitted = true
}
</script>

<template>
  <div
    v-if="showFloatingEntry"
    @keydown.esc="open = false"
  >
    <VBtn
      v-if="!open"
      class="assistant-fab"
      color="primary"
      icon
      size="large"
      position="fixed"
      :aria-label="t('assistant.open')"
      @click="open = true"
    >
      <VIcon icon="tabler-message-chatbot" />
    </VBtn>
    <VNavigationDrawer
      v-model="open"
      location="end"
      temporary
      width="420"
      class="assistant-drawer"
    >
      <AppDrawerHeaderSection
        :title="t('assistant.title')"
        @cancel="open = false"
      />
      <div class="px-6 pb-4 text-caption text-medium-emphasis">
        {{ pageName }}
        <span v-if="selectedId"> · {{ selectedId }}</span>
        <span v-else> · {{ t('assistant.noSelection') }}</span>
        <div class="mt-1">
          {{ t('assistant.disclaimer') }}
        </div>
        <VAlert
          v-if="!aiMode.isEnabled"
          class="mt-3"
          density="compact"
          type="info"
          variant="tonal"
        >
          {{ t('assistant.aiClosed') }}
        </VAlert>
      </div>
      <VDivider />
      <ChatThread
        v-model="draft"
        :messages="bubbles"
        :assistant-name="t('assistant.title')"
        :self-name="session.displayName"
        :placeholder="t('assistant.placeholder')"
        :send-label="t('assistant.send')"
        :loading="sending"
        :state="state"
        :status-text="statusText"
        :ai-enabled="aiMode.isEnabled"
        :disabled-reason="t('assistant.aiClosed')"
        :empty-title="`欢迎使用${t('assistant.title')}`"
        empty-text="我会结合当前页面和权限读取已存储数据；写操作只会形成待审批建议。"
        :suggestions="suggestions"
        source-label="只读数据 · CrossERP 已存储记录"
        @send="send"
        @suggestion="sendMessage"
        @retry="retry"
        @cancel="cancel"
      >
        <template #message-after="{ message }">
          <VCard
            v-if="message.card"
            class="mt-2"
            variant="tonal"
          >
            <VCardItem>
              <VCardTitle class="text-subtitle-1">
                {{ message.card.kind === 'suggestion' ? t('assistant.suggestion') : t('assistant.query') }}
              </VCardTitle>
              <VCardSubtitle>{{ message.card.title }}</VCardSubtitle>
            </VCardItem>
            <VCardText>
              <div
                v-for="line in message.card.lines"
                :key="line.label"
                class="d-flex justify-space-between gap-4 text-body-2"
              >
                <span>{{ line.label }}</span>
                <span>{{ line.value }}</span>
              </div>
              <PermissionGate
                v-if="message.card.draft"
                action="suggest"
              >
                <VBtn
                  class="mt-3"
                  size="small"
                  :disabled="message.submitted"
                  @click="submit(message)"
                >
                  {{ message.submitted ? t('assistant.submitted') : t('assistant.submit') }}
                </VBtn>
              </PermissionGate>
            </VCardText>
          </VCard>
        </template>
      </ChatThread>
    </VNavigationDrawer>
  </div>
</template>

<style scoped>
.assistant-fab {
  z-index: 1006;
  bottom: 24px;
  inset-inline-end: 24px;
}

.assistant-drawer :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.assistant-drawer :deep(.chat-thread) {
  min-block-size: 0;
  flex: 1 1 auto;
}

.assistant-drawer {
  max-inline-size: calc(100vw - 1rem);
}

.assistant-drawer :deep(.chat-thread__log) {
  padding-inline: 1rem;
}

@media (max-width: 600px) {
  .assistant-fab {
    inset-inline-end: 16px;
    bottom: 16px;
  }
}
</style>
