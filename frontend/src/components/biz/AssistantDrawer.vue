<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'
import type { AgentCard, AgentPart } from '@/agent/adapter'
import { createAgentAdapter } from '@/agent/index'
import { submitAgentSuggestion } from '@/api/workflows'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { usePageContext } from '@/composables/usePageContext'
import { pageCatalog } from '@/config/pages'
import { useSessionStore } from '@/stores/session'
import { useAiModeStore } from '@/stores/ai-mode'
import { can } from '@/utils/permission'
import ChatLog from '@/views/apps/chat/ChatLog.vue'
import ChatMessageForm from '@/views/apps/chat/ChatMessageForm.vue'

interface Bubble {
  id: string
  role: 'user' | 'assistant'
  text: string
  card?: AgentCard
  submitted?: boolean
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
const adapter = createAgentAdapter()
const scrollbarRef = ref<unknown>(null)

async function scrollLogToBottom() {
  await nextTick()

  const candidate = scrollbarRef.value as { $el?: HTMLElement } | HTMLElement | null
  const el = (candidate && '$el' in candidate ? candidate.$el : candidate) as HTMLElement | null
  if (el) {
    el.scrollTop = el.scrollHeight
    el.scrollTo?.({ top: el.scrollHeight, behavior: 'smooth' })
  }
}

watch(() => bubbles.value.length, scrollLogToBottom)
watch(sending, scrollLogToBottom)
watch(open, value => {
  if (value)
    scrollLogToBottom()
})

function matchPage(path: string) {
  const ranked = [...pageCatalog].filter(item => item.path !== '/*').sort((a, b) => b.path.length - a.path.length)

  return ranked.find(item => {
    const pattern = `^${item.path.replace(/:[^/]+/g, '[^/]+')}$`

    return new RegExp(pattern).test(path)
  })
}

const page = computed(() => matchPage(route.path))
const pageName = computed(() => page.value?.name[String(locale.value).startsWith('en') ? 'en' : 'zh-CN'] ?? route.path)

const selectedId = computed(() => {
  if (pageContext.selectedRecordId.value)
    return pageContext.selectedRecordId.value

  const params = route.params as Record<string, string | string[] | undefined>
  const value = params.id

  return Array.isArray(value) ? value[0] ?? null : value ?? null
})

const canSuggest = computed(() => can(session.role, 'suggest'))

function pushPart(part: AgentPart) {
  const last = bubbles.value[bubbles.value.length - 1]

  if (part.kind === 'text' && last?.role === 'assistant' && !last.card) {
    last.text += part.text ?? ''

    return
  }

  bubbles.value.push({
    id: `a-${bubbles.value.length + 1}`,
    role: 'assistant',
    text: part.text ?? '',
    card: part.card,
  })
}

async function send() {
  const text = draft.value.trim()

  if (!text || sending.value)
    return

  draft.value = ''
  sending.value = true
  bubbles.value.push({ id: `u-${bubbles.value.length + 1}`, role: 'user', text })
  try {
    await adapter.sendMessage({
      pageName: pageName.value,
      route: route.path,
      selectedId: selectedId.value,
      locale: String(locale.value).startsWith('en') ? 'en' : 'zh-CN',
    }, text, pushPart)
  }
  catch (error) {
    bubbles.value.push({
      id: `e-${bubbles.value.length + 1}`,
      role: 'assistant',
      text: error instanceof Error ? error.message : t('foundation.errorTitle'),
    })
  }
  finally {
    sending.value = false
  }
}

async function submit(bubble: Bubble) {
  if (!bubble.card?.draft || !canSuggest.value)
    return

  await submitAgentSuggestion(bubble.card.draft)
  bubble.submitted = true
}
</script>

<template>
  <div v-if="aiMode.isEnabled">
    <VBtn
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
      class="scrollable-content"
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
      </div>
      <VDivider />
      <PerfectScrollbar
        ref="scrollbarRef"
        :options="{ wheelPropagation: false }"
        class="assistant-log"
      >
        <ChatLog
          :messages="bubbles"
          :contact-name="t('assistant.title')"
          :self-name="session.displayName"
        >
          <template #after="{ message }">
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
        </ChatLog>
        <div
          v-if="sending"
          class="text-caption text-medium-emphasis px-6 pb-4"
        >
          {{ t('assistant.thinking') }}
        </div>
      </PerfectScrollbar>
      <VDivider />
      <ChatMessageForm
        v-model="draft"
        :placeholder="t('assistant.placeholder')"
        :send-label="t('assistant.send')"
        :loading="sending"
        @send="send"
      />
    </VNavigationDrawer>
  </div>
</template>

<style scoped>
.assistant-fab {
  z-index: 1006;
  bottom: 92px;
  inset-inline-end: 24px;
}

.assistant-log {
  max-block-size: calc(100vh - 220px);
}
</style>
