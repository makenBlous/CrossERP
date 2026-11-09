<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  saving?: boolean
  saveDisabled?: boolean
}>()

const emit = defineEmits<{
  save: []
  cancel: []
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
  <!-- 结构改编自 Vuexy ecommerce/product/add：顶栏操作 + 左 8 右 4。 -->
  <div>
    <div class="d-flex flex-wrap justify-start justify-sm-space-between gap-y-4 gap-x-6 mb-6">
      <div class="d-flex flex-column justify-center">
        <h4 class="text-h4 font-weight-medium">
          {{ title }}
        </h4>
        <div
          v-if="subtitle"
          class="text-body-1"
        >
          {{ subtitle }}
        </div>
      </div>
      <div class="d-flex gap-4 align-center flex-wrap">
        <VBtn
          variant="tonal"
          color="secondary"
          @click="emit('cancel')"
        >
          {{ t('foundation.cancel') }}
        </VBtn>
        <VBtn
          :loading="saving"
          :disabled="saveDisabled"
          @click="submit"
        >
          {{ t('foundation.save') }}
        </VBtn>
      </div>
    </div>

    <VForm
      ref="form"
      @submit.prevent="submit"
    >
      <VRow>
        <VCol
          cols="12"
          md="8"
        >
          <VCard
            class="mb-6"
            :title="title"
          >
            <VCardText>
              <slot />
            </VCardText>
          </VCard>
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <slot name="aside" />
        </VCol>
      </VRow>
    </VForm>
  </div>
</template>
