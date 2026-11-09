<script setup lang="ts">
import type { AgentCard, AgentPart } from '@/agent/adapter'
import { createAgentAdapter } from '@/agent/index'
import { submitAgentSuggestion } from '@/api/workflows'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { pageCatalog } from '@/config/pages'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import { can } from '@/utils/permission'

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
const pageContext = usePageContext()
const open = ref(false)
const draft = ref('')
const sending = ref(false)
const bubbles = ref<Bubble[]>([])
const adapter = createAgentAdapter()

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
  <div>
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
    >
      <div class="d-flex flex-column h-100">
        <div class="pa-4">
          <div class="d-flex align-center justify-space-between">
            <h5 class="text-h5 mb-0">
              {{ t('assistant.title') }}
            </h5>
            <VBtn
              icon="tabler-x"
              variant="text"
              @click="open = false"
            />
          </div>
          <div class="text-caption text-medium-emphasis mt-2">
            {{ pageName }}
            <span v-if="selectedId"> · {{ selectedId }}</span>
            <span v-else> · {{ t('assistant.noSelection') }}</span>
          </div>
          <div class="text-caption mt-1">
            {{ t('assistant.disclaimer') }}
          </div>
        </div>
        <VDivider />
        <div class="flex-grow-1 overflow-y-auto pa-4">
          <div
            v-for="bubble in bubbles"
            :key="bubble.id"
            class="mb-4"
          >
            <div
              class="text-caption mb-1"
              :class="bubble.role === 'user' ? 'text-primary' : 'text-medium-emphasis'"
            >
              {{ bubble.role === 'user' ? session.displayName : t('assistant.title') }}
            </div>
            <div
              v-if="bubble.text"
              class="text-body-2"
            >
              {{ bubble.text }}
            </div>
            <VCard
              v-if="bubble.card"
              class="mt-2"
              variant="tonal"
            >
              <VCardItem>
                <VCardTitle class="text-subtitle-1">
                  {{ bubble.card.kind === 'suggestion' ? t('assistant.suggestion') : t('assistant.query') }}
                </VCardTitle>
                <VCardSubtitle>{{ bubble.card.title }}</VCardSubtitle>
              </VCardItem>
              <VCardText>
                <div
                  v-for="line in bubble.card.lines"
                  :key="line.label"
                  class="d-flex justify-space-between gap-4 text-body-2"
                >
                  <span>{{ line.label }}</span>
                  <span>{{ line.value }}</span>
                </div>
                <PermissionGate
                  v-if="bubble.card.draft"
                  action="suggest"
                >
                  <VBtn
                    class="mt-3"
                    size="small"
                    :disabled="bubble.submitted"
                    @click="submit(bubble)"
                  >
                    {{ bubble.submitted ? t('assistant.submitted') : t('assistant.submit') }}
                  </VBtn>
                </PermissionGate>
              </VCardText>
            </VCard>
          </div>
          <div
            v-if="sending"
            class="text-caption text-medium-emphasis"
          >
            {{ t('assistant.thinking') }}
          </div>
        </div>
        <VDivider />
        <div class="pa-4 d-flex gap-2">
          <AppTextField
            v-model="draft"
            :label="t('assistant.placeholder')"
            @keydown.enter.prevent="send"
          />
          <VBtn
            color="primary"
            :loading="sending"
            @click="send"
          >
            {{ t('assistant.send') }}
          </VBtn>
        </div>
      </div>
    </VNavigationDrawer>
  </div>
</template>

<style scoped>
.assistant-fab {
  z-index: 1006;
  bottom: 92px;
  inset-inline-end: 24px;
}
</style>
