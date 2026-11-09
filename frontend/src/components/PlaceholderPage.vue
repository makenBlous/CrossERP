<script setup lang="ts">
import { findPageById, findPageByPath } from '@/config/pages'
import type { PagePhase } from '@/config/pages'
import type { AppLocale } from '@/types/domain'

const route = useRoute()
const { t, locale } = useI18n({ useScope: 'global' })

const page = computed(() => {
  const id = route.meta.pageId

  if (typeof id === 'string') {
    const found = findPageById(id)

    if (found)
      return found
  }

  return findPageByPath(route.path)
})

const appLocale = computed<AppLocale>(() => locale.value === 'en' ? 'en' : 'zh-CN')

const phaseLabel = computed(() => {
  const phase: PagePhase = page.value?.phase ?? 'later'
  if (phase === 'now')
    return t('common.phaseNow')
  if (phase === 'v1')
    return t('common.phaseV1')

  return t('common.phaseLater')
})

const phaseColor = computed(() => {
  if (page.value?.phase === 'now')
    return 'primary'
  if (page.value?.phase === 'v1')
    return 'info'

  return 'warning'
})
</script>

<template>
  <VCard v-if="page">
    <VCardItem>
      <template #prepend>
        <VAvatar
          color="primary"
          variant="tonal"
          rounded
        >
          <VIcon :icon="page.icon" />
        </VAvatar>
      </template>
      <VCardTitle>{{ page.name[appLocale] }}</VCardTitle>
      <VCardSubtitle>{{ page.path }}</VCardSubtitle>
      <template #append>
        <VChip
          :color="phaseColor"
          size="small"
        >
          {{ phaseLabel }}
        </VChip>
      </template>
    </VCardItem>
    <VCardText>
      <VAlert
        type="info"
        variant="tonal"
        class="mb-4"
      >
        {{ t('common.planning') }}
      </VAlert>
      <div class="text-overline text-medium-emphasis">
        {{ t('common.purpose') }}
      </div>
      <p class="text-body-1 mb-4">
        {{ page.purpose[appLocale] }}
      </p>
      <div class="text-overline text-medium-emphasis">
        {{ t('common.blocks') }}
      </div>
      <VList density="compact">
        <VListItem
          v-for="block in page.blocks[appLocale]"
          :key="block"
          prepend-icon="tabler-point"
        >
          <VListItemTitle>{{ block }}</VListItemTitle>
        </VListItem>
      </VList>
    </VCardText>
  </VCard>
  <VAlert
    v-else
    type="warning"
  >
    {{ t('error.title') }}
  </VAlert>
</template>
