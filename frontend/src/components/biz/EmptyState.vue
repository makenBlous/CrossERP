<script setup lang="ts">
defineProps<{
  title?: string
  text?: string
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <VEmptyState
    icon="tabler-inbox"
    :title="title || t('foundation.emptyTitle')"
    :text="text || t('foundation.emptyText')"
  />
</template>
