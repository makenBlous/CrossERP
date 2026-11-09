<script setup lang="ts" generic="T extends { id: string; role: 'user' | 'assistant'; text: string; time?: string }">
export interface ChatBubble {
  id: string
  role: 'user' | 'assistant'
  text: string
  time?: string
}

const props = defineProps<{
  messages: T[]
  contactName: string
  selfName: string
}>()

interface MessageGroup {
  role: ChatBubble['role']
  messages: T[]
}

const groups = computed(() => {
  const result: MessageGroup[] = []

  for (const message of props.messages) {
    const last = result[result.length - 1]

    if (last?.role === message.role)
      last.messages.push(message)
    else
      result.push({ role: message.role, messages: [message] })
  }

  return result
})
</script>

<template>
  <!-- 气泡样式改编自 Vuexy views/apps/chat/ChatLog.vue。不依赖演示用的 chat store。 -->
  <div class="chat-log pa-6">
    <div
      v-for="(group, index) in groups"
      :key="`${group.role}-${index}`"
      class="chat-group d-flex align-start"
      :class="[{
        'flex-row-reverse': group.role === 'user',
        'mb-6': groups.length - 1 !== index,
      }]"
    >
      <div
        class="chat-avatar"
        :class="group.role === 'user' ? 'ms-4' : 'me-4'"
      >
        <VAvatar
          size="32"
          :color="group.role === 'user' ? 'primary' : 'secondary'"
          variant="tonal"
        >
          <span>{{ (group.role === 'user' ? selfName : contactName).slice(0, 1) }}</span>
        </VAvatar>
      </div>
      <div
        class="chat-body d-inline-flex flex-column"
        :class="group.role === 'user' ? 'align-end' : 'align-start'"
      >
        <div
          v-for="(message, msgIndex) in group.messages"
          :key="message.id"
          class="w-100"
        >
          <div
            class="chat-content py-2 px-4 elevation-2"
            style="background-color: rgb(var(--v-theme-surface));"
            :class="[
              group.role === 'assistant' ? 'chat-left' : 'bg-primary text-white chat-right',
              group.messages.length - 1 !== msgIndex ? 'mb-2' : 'mb-1',
            ]"
          >
            <p class="mb-0 text-base">
              {{ message.text }}
            </p>
          </div>
          <slot
            name="after"
            :message="message"
          />
          <div
            class="text-sm text-disabled"
            :class="{ 'text-right': group.role === 'user' }"
          >
            <span v-if="message.time">{{ message.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss">
.chat-log {
  .chat-body {
    max-inline-size: calc(100% - 6.75rem);

    .chat-content {
      border-end-end-radius: 6px;
      border-end-start-radius: 6px;

      p {
        overflow-wrap: anywhere;
      }

      &.chat-left {
        border-start-end-radius: 6px;
      }

      &.chat-right {
        border-start-start-radius: 6px;
      }
    }
  }
}
</style>
