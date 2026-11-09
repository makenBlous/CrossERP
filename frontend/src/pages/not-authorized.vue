<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })

definePage({
  meta: {
    public: false,
  },
})
</script>

<template>
  <VCard
    class="mx-auto mt-8"
    max-width="560"
  >
    <VCardText class="text-center pa-8">
      <VAvatar
        color="warning"
        variant="tonal"
        size="72"
        class="mb-4"
      >
        <VIcon
          icon="tabler-lock"
          size="36"
        />
      </VAvatar>
      <h4 class="text-h4 mb-2">
        {{ t('notAuthorized.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-6">
        {{ t('notAuthorized.desc') }}
      </p>
      <VBtn to="/dashboard">
        {{ t('common.backDashboard') }}
      </VBtn>
    </VCardText>
  </VCard>
</template>
