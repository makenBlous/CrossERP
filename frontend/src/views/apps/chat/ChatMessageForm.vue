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
    class="chat-log-message-form mb-5 mx-5"
    @submit.prevent="emit('send')"
  >
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
      variant="solo"
      density="default"
      class="chat-message-input"
      :placeholder="disabled ? disabledHint : placeholder"
      :disabled="disabled"
      rows="1"
      max-rows="7"
      auto-grow
      @keydown="onKeydown"
    />
    <div class="chat-message-actions d-flex gap-1 align-center">
      <label
        class="chat-message-icon"
        :class="{ 'chat-message-icon--disabled': disabled }"
        title="添加附件"
      >
        <VIcon
          icon="tabler-paperclip"
          size="20"
        />
        <input
          type="file"
          hidden
          :disabled="disabled"
          @change="onFiles"
        >
      </label>
      <span class="text-caption text-disabled me-auto">Enter 发送 · Shift+Enter 换行</span>
      <IconBtn
        :disabled="disabled"
        aria-label="语音输入"
      >
        <VIcon
          icon="tabler-microphone"
          size="22"
        />
      </IconBtn>
      <VBtn
        append-icon="tabler-send"
        :loading="loading"
        :disabled="disabled || !model.trim()"
        type="submit"
      >
        {{ sendLabel }}
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
  </VForm>
</template>

<style lang="scss">
.chat-log-message-form {
  flex: 0 0 auto;
}

.chat-message-input {
  .v-field__input {
    font-size: 0.9375rem !important;
    line-height: 1.375rem !important;
    padding-block: 0.6rem 0.5rem;
  }

  .v-field__append-inner {
    align-items: center;
    padding-block-start: 0;
  }

  .v-field--appended {
    padding-inline-end: 8px;
  }
}

.chat-message-actions {
  margin-block-start: 0.35rem;
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
  .chat-message-actions .text-caption {
    display: none;
  }
}
</style>
