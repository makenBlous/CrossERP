<script setup lang="ts">
withDefaults(defineProps<{
  placeholder: string
  sendLabel: string
  loading?: boolean
  disabled?: boolean
  disabledHint?: string
}>(), {
  loading: false,
  disabled: false,
  disabledHint: '',
})

const emit = defineEmits<{
  send: []
  cancel: []
}>()

const model = defineModel<string>({ required: true })
const attachmentNames = ref<string[]>([])

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('cancel')

    return
  }

  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('send')
  }
}

function onFiles(event: Event) {
  const input = event.target as HTMLInputElement

  attachmentNames.value = [...input.files ?? []].map(file => file.name)
}
</script>

<template>
  <VForm
    class="chat-log-message-form"
    @submit.prevent="emit('send')"
  >
    <div class="chat-composer-shell">
      <div
        v-if="attachmentNames.length"
        class="chat-message-attachments"
      >
        <span
          v-for="name in attachmentNames"
          :key="name"
          class="chat-message-attachment"
        >
          <VIcon
            icon="tabler-paperclip"
            size="14"
          />
          {{ name }}
        </span>
      </div>
      <VTextarea
        v-model="model"
        variant="plain"
        hide-details
        density="comfortable"
        class="chat-message-input"
        :placeholder="disabled ? disabledHint : placeholder"
        :disabled="disabled"
        rows="1"
        max-rows="7"
        auto-grow
        @keydown="onKeydown"
      />
      <div class="chat-message-actions">
        <label
          class="chat-message-icon"
          :class="{ 'chat-message-icon--disabled': disabled }"
          title="添加附件"
        >
          <VIcon
            icon="tabler-plus"
            size="21"
          />
          <input
            type="file"
            hidden
            :disabled="disabled"
            @change="onFiles"
          >
        </label>
        <span class="chat-message-hint">Enter 发送 · Shift+Enter 换行</span>
        <IconBtn
          :disabled="disabled"
          aria-label="语音输入"
          class="chat-message-mic"
        >
          <VIcon
            icon="tabler-microphone"
            size="20"
          />
        </IconBtn>
        <VBtn
          class="chat-send-button"
          color="primary"
          :loading="loading"
          :disabled="disabled || !model.trim()"
          type="submit"
        >
          <VIcon icon="tabler-arrow-up" />
          <span class="chat-send-label">{{ sendLabel }}</span>
        </VBtn>
        <VBtn
          v-if="loading"
          variant="text"
          size="small"
          @click="emit('cancel')"
        >
          取消
        </VBtn>
      </div>
    </div>
  </VForm>
</template>

<style lang="scss">
.chat-log-message-form {
  flex: 0 0 auto;
  margin: .75rem 1.25rem 1.25rem;
}

.chat-composer-shell {
  border: 1px solid rgba(var(--v-theme-on-surface), .12);
  border-radius: 1.25rem;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 8px 24px rgba(43, 46, 60, .08);
  padding: .35rem .55rem .45rem;
}

.chat-message-input {
  .v-field__input {
    min-block-size: 2.5rem;
    padding: .45rem .55rem .3rem;
    font-size: 0.9375rem !important;
    line-height: 1.45rem !important;
  }

  .v-field__append-inner {
    align-items: center;
    padding-block-start: 0;
  }

  .v-field__outline { display: none; }
}

.chat-message-actions {
  display: flex;
  align-items: center;
  min-block-size: 2.25rem;
  gap: .2rem;
}

.chat-message-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2rem;
  block-size: 2rem;
  border-radius: 50%;
  cursor: pointer;
}

.chat-message-icon:hover {
  background: rgba(var(--v-theme-primary), 0.1);
}

.chat-message-icon--disabled {
  cursor: default;
  opacity: 0.45;
}

.chat-message-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-block-end: 0.5rem;
}

.chat-message-hint {
  margin-inline-start: .25rem;
  color: rgba(var(--v-theme-on-surface), .48);
  font-size: .72rem;
}

.chat-message-mic {
  margin-inline-start: auto;
}

.chat-send-button {
  min-inline-size: 2.35rem;
  block-size: 2.35rem;
  border-radius: 999px;
  padding-inline: .7rem;
}

.chat-send-label {
  margin-inline-start: .25rem;
  font-size: .78rem;
}

.chat-message-attachment {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  max-inline-size: 100%;
  border-radius: 0.45rem;
  background: rgba(var(--v-theme-primary), 0.08);
  padding: 0.25rem 0.45rem;
  font-size: 0.72rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 600px) {
  .chat-log-message-form {
    margin: .55rem .65rem .75rem;
  }

  .chat-message-hint,
  .chat-send-label {
    display: none;
  }

  .chat-send-button {
    inline-size: 2.35rem;
    padding: 0;
  }
}
</style>
