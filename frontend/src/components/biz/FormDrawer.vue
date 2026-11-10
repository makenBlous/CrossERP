<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'

const props = defineProps<{
  modelValue: boolean
  title: string
  saving?: boolean
  saveDisabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: []
}>()

const { t } = useI18n({ useScope: 'global' })
const form = ref<{ validate: () => Promise<{ valid: boolean }> }>()

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  const result = await form.value?.validate()

  if (!result?.valid)
    return

  emit('save')
}

function onModel(value: boolean) {
  emit('update:modelValue', value)
}
</script>

<template>
  <!-- 结构改编自 Vuexy apps/user/list/AddNewUserDrawer。 -->
  <VNavigationDrawer
    data-allow-mismatch
    temporary
    :width="400"
    location="end"
    class="scrollable-content"
    :model-value="props.modelValue"
    @update:model-value="onModel"
  >
    <AppDrawerHeaderSection
      :title="title"
      @cancel="close"
    />

    <VDivider />

    <PerfectScrollbar :options="{ wheelPropagation: false }">
      <VCard flat>
        <VCardText>
          <VForm
            ref="form"
            @submit.prevent="submit"
          >
            <VRow>
              <VCol cols="12">
                <slot />
              </VCol>
              <VCol cols="12">
                <VBtn
                  type="submit"
                  class="me-3"
                  :loading="saving"
                  :disabled="props.saveDisabled"
                >
                  {{ t('foundation.save') }}
                </VBtn>
                <VBtn
                  variant="tonal"
                  color="error"
                  @click="close"
                >
                  {{ t('foundation.cancel') }}
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </PerfectScrollbar>
  </VNavigationDrawer>
</template>
