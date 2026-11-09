<script setup lang="ts">
defineProps<{
  title?: string
  text?: string
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="text-center py-10">
    <VIcon
      icon="tabler-inbox"
      size="40"
      class="mb-3 text-medium-emphasis"
    />
    <div class="text-h6">
      {{ title || t('foundation.emptyTitle') }}
    </div>
    <p class="text-body-2 text-medium-emphasis mb-0">
      {{ text || t('foundation.emptyText') }}
    </p>
  </div>
</template>
