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
  <!-- 左栏正文、右栏轨迹，改编自 ecommerce order details；页内标签用 user view 的 v-tabs-pill。 -->
  <div>
    <div class="d-flex justify-space-between align-center flex-wrap gap-y-4 mb-6">
      <div>
        <div class="d-flex gap-2 align-center mb-2 flex-wrap">
          <h5 class="text-h5">
            {{ title }}
          </h5>
          <StatusChip
            v-if="domain && status"
            :domain="domain"
            :value="status"
          />
        </div>
        <div
          v-if="subtitle"
          class="text-body-1"
        >
          {{ subtitle }}
        </div>
      </div>
      <div class="d-flex gap-4 align-center flex-wrap">
        <slot name="actions" />
      </div>
    </div>

    <VRow>
      <VCol
        cols="12"
        md="8"
      >
        <slot />
      </VCol>
      <VCol
        cols="12"
        md="4"
      >
        <VCard
          class="mb-6"
          :title="t('foundation.timeline')"
        >
          <VCardText>
            <VTimeline
              v-if="timeline?.length"
              truncate-line="both"
              line-inset="9"
              align="start"
              side="end"
              line-color="primary"
              density="compact"
            >
              <VTimelineItem
                v-for="(item, index) in timeline"
                :key="item.id || index"
                dot-color="primary"
                size="x-small"
              >
                <div class="d-flex justify-space-between align-center gap-2">
                  <span class="app-timeline-title">
                    {{ item.title }}
                  </span>
                  <span class="app-timeline-meta text-caption text-disabled">
                    {{ item.at }}
                  </span>
                </div>
                <p class="app-timeline-text mb-0 mt-2">
                  {{ item.detail }}
                  <span v-if="item.actor"> · {{ item.actor }}</span>
                </p>
              </VTimelineItem>
            </VTimeline>
            <EmptyState
              v-else
              :text="t('foundation.noTimeline')"
            />
          </VCardText>
        </VCard>
        <VCard :title="t('foundation.related')">
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
