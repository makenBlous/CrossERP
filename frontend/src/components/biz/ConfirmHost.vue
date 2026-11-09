<script setup lang="ts">
import { useConfirm } from '@/composables/useConfirm'

const { pending, settle } = useConfirm()
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <VDialog
    :model-value="pending != null"
    max-width="460"
    @update:model-value="open => { if (!open) settle(false) }"
  >
    <VCard v-if="pending">
      <VCardItem>
        <VCardTitle>{{ pending.options.title }}</VCardTitle>
      </VCardItem>
      <VCardText>{{ pending.options.text }}</VCardText>
      <VCardActions>
        <VSpacer />
        <VBtn
          variant="text"
          @click="settle(false)"
        >
          {{ pending.options.cancelText || t('foundation.cancel') }}
        </VBtn>
        <VBtn
          color="primary"
          @click="settle(true)"
        >
          {{ pending.options.confirmText || t('foundation.confirm') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
