<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  saving?: boolean
}>()

const emit = defineEmits<{
  save: []
}>()

const { t } = useI18n({ useScope: 'global' })
const form = ref<{ validate: () => Promise<{ valid: boolean }> }>()

async function submit() {
  const result = await form.value?.validate()

  if (!result?.valid)
    return

  emit('save')
}
</script>

<template>
  <VCard>
    <VCardItem>
      <VCardTitle>{{ title }}</VCardTitle>
      <VCardSubtitle v-if="subtitle">
        {{ subtitle }}
      </VCardSubtitle>
    </VCardItem>
    <VCardText>
      <VForm
        ref="form"
        @submit.prevent="submit"
      >
        <slot />
        <div class="d-flex justify-end mt-6">
          <VBtn
            color="primary"
            type="submit"
            :loading="saving"
          >
            {{ t('foundation.save') }}
          </VBtn>
        </div>
      </VForm>
    </VCardText>
  </VCard>
</template>
