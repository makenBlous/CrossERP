<script setup lang="ts">
defineProps<{
  placeholder: string
  sendLabel: string
  loading?: boolean
}>()

const emit = defineEmits<{
  send: []
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <!-- 输入条改编自 Vuexy pages/apps/chat.vue 的 chat-message-input。 -->
  <VForm
    class="chat-log-message-form mb-5 mx-5"
    @submit.prevent="emit('send')"
  >
    <VTextField
      v-model="model"
      variant="solo"
      density="default"
      class="chat-message-input"
      :placeholder="placeholder"
      autofocus
      @keydown.enter.prevent="emit('send')"
    >
      <template #append-inner>
        <div class="d-flex gap-1 align-center">
          <IconBtn>
            <VIcon
              icon="tabler-microphone"
              size="22"
            />
          </IconBtn>
          <IconBtn>
            <VIcon
              icon="tabler-paperclip"
              size="22"
            />
          </IconBtn>
          <VBtn
            append-icon="tabler-send"
            :loading="loading"
            @click="emit('send')"
          >
            {{ sendLabel }}
          </VBtn>
        </div>
      </template>
    </VTextField>
  </VForm>
</template>

<style lang="scss">
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
</style>
