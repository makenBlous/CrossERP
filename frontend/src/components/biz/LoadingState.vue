<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <VSkeletonLoader
    type="article, table-row@4"
    :aria-label="t('foundation.loading')"
  />
</template>
