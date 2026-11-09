<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  title: string
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
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

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <VNavigationDrawer
    :model-value="props.modelValue"
    location="end"
    temporary
    width="420"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="pa-6">
      <div class="d-flex align-center justify-space-between mb-6">
        <h5 class="text-h5">
          {{ title }}
        </h5>
        <VBtn
          icon="tabler-x"
          variant="text"
          @click="close"
        />
      </div>
      <VForm
        ref="form"
        @submit.prevent="submit"
      >
        <slot />
        <div class="d-flex justify-end gap-3 mt-6">
          <VBtn
            variant="text"
            @click="close"
          >
            {{ t('foundation.cancel') }}
          </VBtn>
          <VBtn
            color="primary"
            type="submit"
            :loading="saving"
          >
            {{ t('foundation.save') }}
          </VBtn>
        </div>
      </VForm>
    </div>
  </VNavigationDrawer>
</template>
