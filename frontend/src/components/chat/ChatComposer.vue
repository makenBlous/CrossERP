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
const textarea = ref<HTMLTextAreaElement | null>(null)
const attachmentNames = ref<string[]>([])

function resize() {
  const element = textarea.value
  if (!element)
    return

  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 180)}px`
}

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

watch(model, () => nextTick(resize))
onMounted(resize)
</script>

<template>
  <form
    class="chat-composer"
    @submit.prevent="emit('send')"
  >
    <div
      v-if="attachmentNames.length"
      class="chat-composer__attachments"
    >
      <span
        v-for="name in attachmentNames"
        :key="name"
        class="chat-composer__attachment"
      >
        <VIcon
          icon="tabler-paperclip"
          size="14"
        />
        {{ name }}
      </span>
    </div>
    <textarea
      ref="textarea"
      v-model="model"
      class="chat-composer__input"
      :placeholder="disabled ? disabledHint : placeholder"
      :disabled="disabled"
      rows="1"
      @input="resize"
      @keydown="onKeydown"
    />
    <div class="chat-composer__actions">
      <label
        class="chat-composer__icon"
        :class="{ 'chat-composer__icon--disabled': disabled }"
        title="添加附件"
      >
        <VIcon
          icon="tabler-plus"
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
          size="20"
        />
      </IconBtn>
      <VBtn
        icon
        color="primary"
        size="small"
        :loading="loading"
        :disabled="disabled || !model.trim()"
        :aria-label="sendLabel"
        type="submit"
      >
        <VIcon icon="tabler-arrow-up" />
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
  </form>
</template>

<style scoped lang="scss">
.chat-composer {
  flex: 0 0 auto;
  margin: .9rem;
  border: 1px solid rgba(var(--v-theme-on-surface), .12);
  border-radius: 1rem;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 6px 24px rgba(24, 31, 56, .08);
  padding: .7rem .8rem .6rem;
}

.chat-composer__input {
  display: block;
  inline-size: 100%;
  min-block-size: 1.5rem;
  max-block-size: 180px;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: 1.5;
  overflow-y: auto;
}

.chat-composer__input::placeholder {
  color: rgba(var(--v-theme-on-surface), .5);
}

.chat-composer__actions {
  display: flex;
  align-items: center;
  gap: .25rem;
  min-block-size: 2rem;
  margin-block-start: .35rem;
}

.chat-composer__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2rem;
  block-size: 2rem;
  border-radius: 50%;
  cursor: pointer;
}

.chat-composer__icon:hover {
  background: rgba(var(--v-theme-primary), .1);
}

.chat-composer__icon--disabled {
  cursor: default;
  opacity: .45;
}

.chat-composer__attachments {
  display: flex;
  flex-wrap: wrap;
  gap: .4rem;
  margin-block-end: .5rem;
}

.chat-composer__attachment {
  display: inline-flex;
  align-items: center;
  gap: .25rem;
  max-inline-size: 100%;
  border-radius: .45rem;
  background: rgba(var(--v-theme-primary), .08);
  padding: .25rem .45rem;
  font-size: .72rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 600px) {
  .chat-composer {
    margin: .65rem;
  }

  .chat-composer__actions .text-caption {
    display: none;
  }
}
</style>
