<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="d-flex align-center justify-center gap-3 py-10">
    <VProgressCircular
      indeterminate
      color="primary"
      size="28"
    />
    <span class="text-body-1">{{ t('foundation.loading') }}</span>
  </div>
</template>
