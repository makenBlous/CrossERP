<script setup lang="ts" generic="T extends { id: string; role: 'user' | 'assistant'; text: string; time?: string }">
import { parseSafeMarkdown } from '@/components/chat/markdown'

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
  padded?: boolean
  sourceLabel?: string
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
  <div
    class="chat-log"
    :class="{ 'chat-log--padded': props.padded !== false }"
  >
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
          v-if="group.role === 'assistant'"
          class="chat-group-meta"
        >
          <span class="chat-sender">{{ contactName }}</span>
          <span
            v-if="props.sourceLabel"
            class="chat-source-chip"
          >
            <VIcon
              icon="tabler-database"
              size="13"
            />
            {{ props.sourceLabel }}
          </span>
        </div>
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
            <div class="chat-markdown text-base">
              <template
                v-for="(block, blockIndex) in parseSafeMarkdown(message.text)"
                :key="`${message.id}-${blockIndex}`"
              >
                <pre
                  v-if="block.type === 'code'"
                  class="chat-code"
                ><code v-text="block.text" /></pre>
                <ul
                  v-else-if="block.type === 'list'"
                  class="chat-list"
                >
                  <li
                    v-for="(item, itemIndex) in block.items"
                    :key="`${message.id}-${blockIndex}-${itemIndex}`"
                    v-text="item"
                  />
                </ul>
                <div
                  v-else-if="block.type === 'table'"
                  class="chat-table-wrap"
                >
                  <table class="chat-table">
                    <thead>
                      <tr>
                        <th
                          v-for="header in block.headers ?? []"
                          :key="header"
                        >
                          {{ header }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, rowIndex) in block.rows ?? []"
                        :key="`${message.id}-${blockIndex}-row-${rowIndex}`"
                      >
                        <td
                          v-for="(cell, cellIndex) in row"
                          :key="`${message.id}-${blockIndex}-${rowIndex}-${cellIndex}`"
                        >
                          {{ cell }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p
                  v-else
                  class="chat-paragraph"
                  v-text="block.text"
                />
              </template>
            </div>
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
  display: flex;
  min-block-size: 100%;
  flex-direction: column;
  gap: 1.35rem;

  &--padded {
    padding: 1.5rem;
  }

  .chat-group {
    inline-size: 100%;
  }

  .chat-body {
    min-inline-size: 0;
    max-inline-size: min(88%, 860px);

    .chat-group-meta {
      display: flex;
      align-items: center;
      gap: .5rem;
      margin-block-end: .45rem;
      color: rgba(var(--v-theme-on-surface), .62);
      font-size: .75rem;
    }

    .chat-sender {
      color: rgba(var(--v-theme-on-surface), .78);
      font-weight: 600;
    }

    .chat-source-chip {
      display: inline-flex;
      align-items: center;
      gap: .25rem;
      border-radius: 999px;
      background: rgba(var(--v-theme-primary), .08);
      padding: .18rem .5rem;
      white-space: nowrap;
    }

    .chat-content {
      border: 1px solid rgba(var(--v-theme-on-surface), .08);
      border-radius: 1.15rem;
      padding: .95rem 1.15rem !important;
      box-shadow: 0 5px 18px rgba(43, 46, 60, .06) !important;

      .chat-paragraph {
        margin-block: 0 .7rem;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        line-height: 1.7;

        &:last-child {
          margin-block-end: 0;
        }
      }

      .chat-list {
        margin-block: 0 .7rem;
        padding-inline-start: 1.2rem;
        line-height: 1.7;
      }

      .chat-code {
        max-inline-size: 100%;
        margin-block: 0;
        border-radius: 0.5rem;
        background: rgba(0, 0, 0, 0.28);
        color: #f4f6ff;
        overflow: auto;
        padding: 0.65rem;
        white-space: pre;
      }

      &.chat-left {
        background: rgba(var(--v-theme-primary), .045) !important;
        border-start-start-radius: .45rem;
      }

      &.chat-right {
        border: 0;
        border-start-end-radius: .45rem;
        box-shadow: 0 7px 18px rgba(var(--v-theme-primary), .2) !important;
      }
    }

    .chat-table-wrap {
      max-inline-size: 100%;
      margin-block: .35rem .7rem;
      overflow-x: auto;
    }

    .chat-table {
      inline-size: 100%;
      border-collapse: collapse;
      font-size: .875rem;

      th,
      td {
        border-block-end: 1px solid rgba(var(--v-theme-on-surface), .1);
        padding: .55rem .65rem;
        text-align: start;
        white-space: nowrap;
      }

      th {
        color: rgba(var(--v-theme-on-surface), .72);
        font-weight: 600;
      }
    }
  }

  .chat-group.flex-row-reverse .chat-body {
    max-inline-size: min(78%, 680px);
  }
}

@media (max-width: 600px) {
  .chat-log {
    gap: 1rem;

    .chat-avatar {
      display: none;
    }

    .chat-body,
    .chat-group.flex-row-reverse .chat-body {
      max-inline-size: 94%;
    }

    .chat-content {
      padding: .8rem .95rem !important;
    }

    .chat-source-chip {
      max-inline-size: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}
</style>
