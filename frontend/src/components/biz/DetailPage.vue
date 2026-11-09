<script setup lang="ts">
import type { StatusDomain } from '@/config/status'

defineProps<{
  title: string
  subtitle?: string
  domain?: StatusDomain
  status?: string
  timeline?: Array<{ id?: string; at: string; title: string; detail: string; actor?: string }>
  related?: Array<{ id: string; type: string; label: string; to?: string }>
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-start gap-4 mb-6">
      <div>
        <div class="d-flex flex-wrap align-center gap-3">
          <h4 class="text-h4">
            {{ title }}
          </h4>
          <StatusChip
            v-if="domain && status"
            :domain="domain"
            :value="status"
          />
        </div>
        <p
          v-if="subtitle"
          class="text-body-1 text-medium-emphasis mb-0"
        >
          {{ subtitle }}
        </p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <slot name="actions" />
      </div>
    </div>

    <VRow>
      <VCol
        cols="12"
        lg="8"
      >
        <slot />
      </VCol>
      <VCol
        cols="12"
        lg="4"
      >
        <VCard class="mb-4">
          <VCardItem>
            <VCardTitle>{{ t('foundation.timeline') }}</VCardTitle>
          </VCardItem>
          <VCardText>
            <VTimeline
              v-if="timeline?.length"
              density="compact"
              side="end"
            >
              <VTimelineItem
                v-for="(item, index) in timeline"
                :key="item.id || index"
                dot-color="primary"
                size="x-small"
              >
                <div class="text-subtitle-2">
                  {{ item.title }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ item.at }} <span v-if="item.actor">· {{ item.actor }}</span>
                </div>
                <div class="text-body-2">
                  {{ item.detail }}
                </div>
              </VTimelineItem>
            </VTimeline>
            <EmptyState
              v-else
              :text="t('foundation.noTimeline')"
            />
          </VCardText>
        </VCard>
        <VCard>
          <VCardItem>
            <VCardTitle>{{ t('foundation.related') }}</VCardTitle>
          </VCardItem>
          <VList v-if="related?.length">
            <VListItem
              v-for="item in related"
              :key="item.id"
              :to="item.to"
            >
              <VListItemTitle>{{ item.label }}</VListItemTitle>
              <VListItemSubtitle>{{ item.type }}</VListItemSubtitle>
            </VListItem>
          </VList>
          <VCardText v-else>
            {{ t('foundation.noRelated') }}
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
