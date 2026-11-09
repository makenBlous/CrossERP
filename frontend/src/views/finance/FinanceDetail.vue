<script setup lang="ts">
import DetailPage from '@/components/biz/DetailPage.vue'
import type { StatusDomain } from '@/config/status'

defineProps<{
  title: string
  subtitle?: string
  status?: string
  domain?: StatusDomain
  timeline?: Array<{ at: string; title: string; detail: string; actor?: string }>
}>()
</script>

<template>
  <DetailPage
    :title="title"
    :subtitle="subtitle"
    :status="status"
    :domain="domain"
    :timeline="timeline"
  >
    <template #actions>
      <slot name="actions" />
    </template>
    <slot />
  </DetailPage>
</template>
