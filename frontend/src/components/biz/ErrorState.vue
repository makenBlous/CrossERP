<script setup lang="ts">
defineProps<{
  text?: string
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <!-- 失败提示沿用 Vuexy 页面里的 VAlert，不另做一套错误卡片。 -->
  <VAlert
    type="error"
    variant="tonal"
  >
    <div class="d-flex flex-wrap align-center justify-space-between gap-3">
      <div>
        <div class="text-subtitle-1">
          {{ t('foundation.errorTitle') }}
        </div>
        <div v-if="text">
          {{ text }}
        </div>
      </div>
      <VBtn
        size="small"
        variant="outlined"
        @click="emit('retry')"
      >
        {{ t('foundation.retry') }}
      </VBtn>
    </div>
  </VAlert>
</template>
