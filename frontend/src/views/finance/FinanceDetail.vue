<script setup lang="ts">
import DetailPage from '@/components/biz/DetailPage.vue'

defineProps<{
  title: string
  subtitle?: string
  status?: string
  domain?: 'approval' | 'issue' | 'voucher' | 'shipment' | 'mapping'
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
