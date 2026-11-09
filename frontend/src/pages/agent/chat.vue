<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'
import { fetchChat } from '@/api/agent'
import { useSessionStore } from '@/stores/session'
import type { ChatMessage, ChatThread } from '@/types/domain'
import ChatLog from '@/views/apps/chat/ChatLog.vue'
import ChatMessageForm from '@/views/apps/chat/ChatMessageForm.vue'

definePage({
  meta: {
    layoutWrapperClasses: 'layout-content-height-fixed',
  },
})

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { isLeftSidebarOpen } = useResponsiveLeftSidebar()
const threads = ref<ChatThread[]>([])
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const activeId = ref('th-1')
const query = ref('')

const canSubmit = computed(() => session.role === 'admin' || session.role === 'operator' || session.role === 'finance')
const activeThread = computed(() => threads.value.find(item => item.id === activeId.value))

const visibleThreads = computed(() => {
  const text = query.value.trim().toLowerCase()

  return threads.value.filter(item => item.title.toLowerCase().includes(text))
})

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

function openThread(id: string) {
  activeId.value = id
  isLeftSidebarOpen.value = false
}
</script>

<template>
  <!-- 布局改编自 Vuexy pages/apps/chat.vue + ChatLog / 消息输入条。 -->
  <VLayout
    class="chat-app-layout"
    style="z-index: 0;"
  >
    <VNavigationDrawer
      v-model="isLeftSidebarOpen"
      data-allow-mismatch
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
          @click="openThread(thread.id)"
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
            <p class="mb-0 text-truncate text-body-2">
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
              {{ t('chat.subtitle') }}
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
          :options="{ wheelPropagation: false }"
          class="flex-grow-1"
        >
          <ChatLog
            :messages="messages"
            :contact-name="t('chat.title')"
            :self-name="session.displayName"
          >
            <template #after="{ message }">
              <VCard
                v-if="message.toolCall"
                variant="tonal"
                color="info"
                class="mt-2"
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
                class="mt-2"
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
            </template>
          </ChatLog>
        </PerfectScrollbar>
        <VDivider />
        <ChatMessageForm
          v-model="draft"
          :placeholder="t('chat.placeholder')"
          :send-label="t('chat.send')"
          @send="send"
        />
      </div>
    </VMain>
  </VLayout>
</template>

<style lang="scss">
@use "@styles/variables/vuetify";
@use "@core/scss/base/mixins";

$chat-app-header-height: 76px;

%chat-header {
  display: flex;
  align-items: center;
  min-block-size: $chat-app-header-height;
  padding-inline: 1.5rem;
}

.chat-app-layout {
  border-radius: vuetify.$card-border-radius;

  @include mixins.elevation(vuetify.$card-elevation);

  .chat-list-header,
  .active-chat-header {
    @extend %chat-header;
  }
}

.chat-contact {
  border-radius: 0.375rem;
  padding-block: 0.75rem;
  padding-inline: 0.75rem;

  &.chat-contact-active {
    background: rgba(var(--v-theme-primary), 0.12);
  }
}
</style>
