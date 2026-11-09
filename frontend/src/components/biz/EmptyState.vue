<script setup lang="ts">
const props = defineProps<{
  title?: string
  text?: string
  backTo?: string
  backLabel?: string
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <VEmptyState
    icon="tabler-inbox"
    :title="title || t('foundation.emptyTitle')"
    :text="text || t('foundation.emptyText')"
  />
  <VBtn
    v-if="props.backTo"
    class="mt-4"
    variant="tonal"
    :to="props.backTo"
  >
    {{ props.backLabel || t('common.backDashboard') }}
  </VBtn>
</template>
